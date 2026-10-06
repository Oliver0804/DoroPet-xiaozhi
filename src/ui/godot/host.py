"""啟動 Godot 視窗，並用本機 TCP 跟它說話."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path

from src.logging import get_logger
from src.ui.godot.protocol import decode_messages, encode_message

logger = get_logger()

MessageHandler = Callable[[dict], None]


def _search_roots() -> list[Path]:
    """原始碼樹，或 PyInstaller 解開後資料所在的目錄."""
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        roots.append(exe.parent)
        roots.append(exe.parent / "_internal")
        contents = exe.parent.parent
        roots.extend(
            [
                contents / "Resources",
                contents / "Frameworks",
                contents / "MacOS",
            ]
        )
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass))
    roots.append(Path(__file__).resolve().parents[3])
    return roots


def godot_project_dir() -> Path:
    for root in _search_roots():
        candidate = root / "godot_ui"
        if (candidate / "project.godot").is_file():
            return candidate
    return Path(__file__).resolve().parents[3] / "godot_ui"


PROJECT_DIR = godot_project_dir()


def find_godot() -> str | None:
    bundled: list[Path] = []
    for root in _search_roots():
        bundled.extend(
            [
                root / "vendor" / "godot" / "Godot.app" / "Contents" / "MacOS" / "Godot",
                root / "vendor" / "godot" / "Godot.exe",
                root / "vendor" / "godot" / "godot",
            ]
        )
    candidates = [os.environ.get("GODOT_BIN", ""), *[str(path) for path in bundled]]
    candidates.extend(
        [
            "/Applications/Godot.app/Contents/MacOS/Godot",
            os.path.expanduser("~/Applications/Godot.app/Contents/MacOS/Godot"),
            "/Applications/Godot_mono.app/Contents/MacOS/Godot",
        ]
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    from shutil import which

    return which("godot") or which("godot4")


class GodotHost:
    """整個行程共用一個 Godot 視窗."""

    _instance: GodotHost | None = None

    def __init__(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._ready = asyncio.Event()
        self._handlers: list[MessageHandler] = []
        self._server: socket.socket | None = None
        self._conn: socket.socket | None = None
        self._pending: list[bytes] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._proc: subprocess.Popen | None = None
        self.port = 0

    @classmethod
    def get(cls) -> GodotHost:
        if cls._instance is None:
            cls._instance = GodotHost()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def subscribe(self, handler: MessageHandler) -> None:
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unsubscribe(self, handler: MessageHandler) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def ensure(self, role: str) -> None:
        """視窗已在就切畫面，否則啟動 Godot."""
        if self._proc is not None and self._proc.poll() is None:
            self.send({"type": "phase", "name": role})
            return
        binary = find_godot()
        if binary is None:
            raise RuntimeError(
                "找不到 Godot。請安裝 Godot 4，或設定 GODOT_BIN 指向執行檔"
            )
        if not PROJECT_DIR.is_dir():
            raise RuntimeError(f"找不到 Godot 專案: {PROJECT_DIR}")
        self._ensure_extension_list(binary)
        self._listen()
        self._stop.clear()
        self._ready = asyncio.Event()
        self._thread = threading.Thread(
            target=self._serve, name="godot-ui", daemon=True
        )
        self._thread.start()
        log_path = _log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = open(log_path, "ab", buffering=0)
        logger.info("啟動 Godot 介面 role=%s port=%s", role, self.port)
        self._proc = subprocess.Popen(
            [
                binary,
                "--path",
                str(PROJECT_DIR),
                "--",
                "--port",
                str(self.port),
                "--role",
                role,
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=60)
        except asyncio.TimeoutError as exc:
            raise RuntimeError(
                f"Godot 介面沒有在 60 秒內連上。日誌: {log_path}"
            ) from exc

    def send(self, payload: dict) -> None:
        raw = encode_message(payload)
        with self._lock:
            conn = self._conn
            if conn is None:
                self._pending.append(raw)
                return
            try:
                conn.sendall(raw)
            except OSError:
                self._conn = None
                self._pending.append(raw)

    async def stop(self) -> None:
        self.send({"type": "quit"})
        self._stop.set()
        proc = self._proc
        self._proc = None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                await asyncio.wait_for(asyncio.to_thread(proc.wait), timeout=3)
            except asyncio.TimeoutError:
                proc.kill()
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except OSError:
                    pass
                self._conn = None
            if self._server is not None:
                try:
                    self._server.close()
                except OSError:
                    pass
                self._server = None
        GodotHost._instance = None

    def _ensure_extension_list(self, binary: str) -> None:
        """第一次打開專案時，Godot 要先掃描才會載入 gd_cubism."""
        marker = PROJECT_DIR / ".godot" / "extension_list.cfg"
        if marker.exists():
            return
        logger.info("第一次啟動，匯入 Godot 外掛")
        subprocess.run(
            [binary, "--headless", "--import", "--path", str(PROJECT_DIR)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=120,
        )

    def _listen(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(0.5)
        self._server = server
        self.port = server.getsockname()[1]

    def _serve(self) -> None:
        assert self._server is not None
        while not self._stop.is_set():
            try:
                conn, _addr = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self._lock:
                self._conn = conn
                pending = self._pending
                self._pending = []
            for raw in pending:
                try:
                    conn.sendall(raw)
                except OSError:
                    return
            self._read(conn)
            return

    def _read(self, conn: socket.socket) -> None:
        buffer = b""
        while not self._stop.is_set():
            try:
                chunk = conn.recv(65536)
            except OSError:
                return
            if not chunk:
                return
            buffer += chunk
            try:
                messages, buffer = decode_messages(buffer)
            except Exception:
                logger.warning("Godot 訊息不是 JSON", exc_info=True)
                continue
            for message in messages:
                self._loop.call_soon_threadsafe(self._deliver, message)

    def _deliver(self, message: dict) -> None:
        if message.get("type") == "ready":
            self._ready.set()
        for handler in list(self._handlers):
            try:
                handler(message)
            except Exception:
                logger.warning("Godot 訊息處理失敗", exc_info=True)


def _log_path() -> Path:
    try:
        from src.utils.resource_finder import get_user_data_dir

        return get_user_data_dir() / "logs" / "godot.log"
    except Exception:
        return PROJECT_DIR / "godot.log"
