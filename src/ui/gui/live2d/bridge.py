"""给 QML 和音频线程用的 Live2D 接缝."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.logging import get_logger
from src.ui.gui.live2d.canvas import Live2DCanvas
from src.ui.gui.live2d.driver import Live2DDriver
from src.ui.gui.live2d.mouth import MouthMeter
from src.ui.gui.live2d.paths import resolve_live2d_model

logger = get_logger()


class Live2DBridge(QObject):
    """主窗口表情区的 Live2D 脸.

    ``ready`` 为真时 QML 藏起 GIF，并把表情区矩形报过来.
    """

    readyChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._driver = Live2DDriver()
        self._meter = MouthMeter()
        self._canvas: Live2DCanvas | None = None
        self._root = None
        self._codec = None
        self._ready = False
        self._enabled = True
        self._local: tuple[float, float, float, float] | None = None
        self._live2d_started = False
        self._closing = False
        self._load_settings()

    def _load_settings(self) -> None:
        try:
            from src.utils.config_manager import get_config
            from src.utils.resource_finder import get_assets_dir

            cfg = get_config()
            self._enabled = bool(cfg.get_config("LIVE2D.ENABLED", True))
            configured = cfg.get_config("LIVE2D.MODEL_PATH", "") or ""
            self._scale = float(cfg.get_config("LIVE2D.SCALE", 0.9) or 0.9)
            self._offset_x = float(cfg.get_config("LIVE2D.OFFSET_X", 0.0) or 0.0)
            self._offset_y = float(cfg.get_config("LIVE2D.OFFSET_Y", 0.08) or 0.08)
            assets = get_assets_dir()
        except Exception as exc:
            logger.debug("读取 Live2D 配置失败，用默认值: %s", exc)
            self._enabled = True
            configured = ""
            self._scale = 0.9
            self._offset_x = 0.0
            self._offset_y = 0.08
            assets = None
        self._model_path = resolve_live2d_model(configured, assets)

    @Property(bool, notify=readyChanged)
    def ready(self) -> bool:
        return self._ready

    def set_emotion(self, emotion: str) -> None:
        self._driver.set_emotion(emotion)

    def bind_codec(self, codec) -> None:
        """把 TTS PCM 接到嘴型. ``codec`` 为 None 时解开."""
        if codec is self._codec:
            return
        self.unbind_codec()
        if codec is None:
            return
        adder = getattr(codec, "add_tts_pcm_listener", None)
        if not callable(adder):
            return
        adder(self._meter.push)
        self._codec = codec

    def unbind_codec(self) -> None:
        codec = self._codec
        self._codec = None
        if codec is None:
            return
        remover = getattr(codec, "remove_tts_pcm_listener", None)
        if callable(remover):
            remover(self._meter.push)

    def attach(self, root_window) -> None:
        """挂到已经显示的主窗口上。失败时维持 GIF."""
        if not self._enabled:
            logger.info("LIVE2D.ENABLED=false，继续使用 GIF 表情")
            return
        if root_window is None:
            return
        if self._model_path is None:
            logger.warning(
                "找不到 Live2D 模型。把 model3.json 放到 assets/live2d/，"
                "或设置 LIVE2D.MODEL_PATH / XIAOZHI_LIVE2D_MODEL"
            )
            return
        try:
            import live2d
        except ImportError:
            logger.warning(
                "未安装 live2d-py（需要 Python 3.11+：uv sync --extra gui --extra live2d），"
                "继续使用 GIF 表情"
            )
            return
        if not self._live2d_started:
            live2d.init()
            self._live2d_started = True

        self._root = root_window
        self._canvas = Live2DCanvas(
            self._driver,
            self._meter,
            self._model_path,
            scale=self._scale,
            offset_x=self._offset_x,
            offset_y=self._offset_y,
        )
        self._canvas.loaded.connect(self._on_loaded)
        self._canvas.failed.connect(self._on_failed)
        self._canvas.setParent(root_window)
        self._canvas.hide()
        root_window.visibilityChanged.connect(self._on_root_visibility)
        logger.info("Live2D 准备绘制: %s", self._model_path)

    @Slot(float, float, float, float)
    def setViewport(self, x: float, y: float, w: float, h: float) -> None:
        """QML 表情区在主窗口里的矩形."""
        self._local = (x, y, w, h)
        self._apply_geometry()

    def shutdown(self) -> None:
        self._closing = True
        root = self._root
        self._root = None
        if root is not None:
            try:
                root.visibilityChanged.disconnect(self._on_root_visibility)
            except (RuntimeError, TypeError):
                pass
        self.unbind_codec()
        canvas = self._canvas
        self._canvas = None
        self._ready = False
        if canvas is not None:
            canvas.release_model()
            canvas.hide()
            canvas.setParent(None)
            canvas.destroy()
        if self._live2d_started:
            try:
                import live2d

                live2d.dispose()
            except Exception as exc:
                logger.debug("live2d.dispose: %s", exc)
            self._live2d_started = False

    def _on_loaded(self) -> None:
        self._ready = True
        self.readyChanged.emit()
        self._apply_geometry()

    def _on_failed(self, message: str) -> None:
        logger.error("Live2D 不可用，回退 GIF: %s", message)
        self._ready = False
        self.readyChanged.emit()
        if self._canvas is not None:
            self._canvas.hide()

    def _on_root_visibility(self, _visibility=None) -> None:
        if self._closing:
            return
        self._apply_geometry()

    def _apply_geometry(self) -> None:
        if self._closing:
            return
        canvas = self._canvas
        root = self._root
        if canvas is None or root is None or self._local is None:
            return
        try:
            visible = root.isVisible()
        except RuntimeError:
            return
        x, y, w, h = self._local
        # 第一次 show 才会走 initializeGL；ready 之前也要给一块区域，否则永远不加载。
        if w < 2 or h < 2 or not visible:
            canvas.hide()
            return
        canvas.setGeometry(int(x), int(y), int(w), int(h))
        if not canvas.isVisible():
            canvas.show()
