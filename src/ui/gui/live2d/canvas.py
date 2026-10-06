"""把 Live2D 画进主窗口里的一块 OpenGL 子窗口.

macOS 上 Qt Quick 走 Metal，离屏 FBO 接不住 Cubism 的绘制，
所以跟官方 live2d-py 示例一样用真正的 OpenGL 窗口，再挂到主窗口上.
"""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Signal
from PySide6.QtGui import QCursor
from PySide6.QtOpenGL import QOpenGLWindow

from src.logging import get_logger
from src.ui.gui.live2d.driver import Live2DDriver
from src.ui.gui.live2d.mouth import MouthMeter

logger = get_logger()

# 鼠标离开角色中心多少像素记为视线 ±1
_GAZE_RANGE_PX = 600.0
_IDLE_TRIGGER_SEC = 3.0


class Live2DCanvas(QOpenGLWindow):
    """Doro（或任意 model3）的绘制表面."""

    loaded = Signal()
    failed = Signal(str)

    def __init__(
        self,
        driver: Live2DDriver,
        meter: MouthMeter,
        model_path: Path,
        scale: float = 0.9,
        offset_x: float = 0.0,
        offset_y: float = 0.08,
    ) -> None:
        super().__init__()
        self._driver = driver
        self._meter = meter
        self._model_path = model_path
        self._scale = scale
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._model = None
        self._known_expressions: set[str] = set()
        self._bad_params: set[str] = set()
        self._pose: dict[str, float] = {}
        self._pending_expression: str | None = None
        self._last_tick = time.monotonic()
        self._last_cursor: QPoint | None = None
        self._idle_time = 0.0
        self._failed = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._on_tick)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt 虚函数名
        super().showEvent(event)
        if not self._timer.isActive():
            self._last_tick = time.monotonic()
            self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def initializeGL(self) -> None:
        try:
            import live2d

            live2d.glInit()
            model = live2d.Model()
            model.LoadModelJson(str(self._model_path))
            self._model = model
            self._known_expressions = set(model.GetExpressions() or [])
            self._apply_layout()
            model.SetAutoBlink(False)
            model.SetAutoBreath(True)
            groups = model.GetMotionGroups() or {}
            if "Idle" in groups:
                model.StartMotion("Idle", 0, live2d.MotionPriority.IDLE)
            logger.info(
                "Live2D 已加载 %s（表情 %s）",
                self._model_path.name,
                ", ".join(sorted(self._known_expressions)),
            )
            self.loaded.emit()
        except Exception as exc:
            self._failed = True
            logger.error("Live2D 初始化失败: %s", exc, exc_info=True)
            self.failed.emit(str(exc))

    def resizeGL(self, w: int, h: int) -> None:
        if self._model is not None and w > 0 and h > 0:
            self._model.Resize(w, h)
            self._apply_layout()

    def paintGL(self) -> None:
        if self._model is None or self._failed:
            return
        import live2d

        model = self._model
        expr = self._pending_expression
        self._pending_expression = None
        if expr is not None:
            self._apply_expression(expr)
        live2d.clearBuffer(1.0, 1.0, 1.0, 1.0)
        model.Update()
        for name, value in self._pose.items():
            if name in self._bad_params:
                continue
            try:
                model.SetParamById(name, float(value), 1.0)
            except Exception:
                self._bad_params.add(name)
                logger.warning("模型没有参数 %s，后续跳过", name)
        model.Draw()

    def release_model(self) -> None:
        """在上下文还在时拆掉渲染器."""
        self._timer.stop()
        model = self._model
        self._model = None
        if model is None:
            return
        try:
            self.makeCurrent()
            model.DestroyRenderer()
            self.doneCurrent()
        except Exception as exc:
            logger.debug("释放 Live2D 渲染器: %s", exc)

    def _apply_layout(self) -> None:
        model = self._model
        if model is None:
            return
        model.SetScale(self._scale)
        model.SetOffset(self._offset_x, self._offset_y)

    def _apply_expression(self, name: str) -> None:
        model = self._model
        if model is None:
            return
        if not name:
            model.ResetExpression()
            return
        if name not in self._known_expressions:
            logger.warning("模型没有表情 %s", name)
            return
        model.SetExpression(name)

    def _on_tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now
        dx, dy, idle, idle_for = self._sample_pointer(dt)
        self._pose = self._driver.tick(dt, dx, dy, idle, idle_for, self._meter.level())
        expr = self._driver.consume_expression()
        if expr is not None:
            self._pending_expression = expr
        self.update()

    def _sample_pointer(self, dt: float) -> tuple[float, float, bool, float]:
        cursor = QCursor.pos()
        if self._last_cursor is None:
            self._last_cursor = cursor
        moved = abs(cursor.x() - self._last_cursor.x()) + abs(
            cursor.y() - self._last_cursor.y()
        )
        self._last_cursor = QPoint(cursor)
        if moved > 2:
            self._idle_time = 0.0
        else:
            self._idle_time += dt
        center = self.mapToGlobal(
            QPoint(max(self.width(), 1) // 2, max(self.height(), 1) // 2)
        )
        dx = max(-1.0, min(1.0, (cursor.x() - center.x()) / _GAZE_RANGE_PX))
        dy = max(-1.0, min(1.0, (cursor.y() - center.y()) / _GAZE_RANGE_PX))
        idle = self._idle_time >= _IDLE_TRIGGER_SEC
        idle_for = max(0.0, self._idle_time - _IDLE_TRIGGER_SEC)
        return dx, dy, idle, idle_for
