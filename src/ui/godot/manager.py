"""Godot 介面的 ViewPort."""

from __future__ import annotations

import time

from src.core.event_bus import EventBus, Events
from src.logging import get_logger
from src.ui.godot.host import GodotHost
from src.ui.shared.events import UISendTextRequest

logger = get_logger()


class GodotViewManager:
    """把狀態畫到 Godot，把按鈕收進事件匯流排."""

    def __init__(self, event_bus: EventBus, task_manager=None):
        self._event_bus = event_bus
        self._tasks = task_manager
        self._host: GodotHost | None = None
        self._running = False
        self._auto_mode = True
        self._codec = None
        self._mouth_at = 0.0
        self._discord_on = False
        self._tts_chunks: list = []
        self._was_speaking = False
        self._state = {
            "type": "state",
            "status": "待命",
            "connected": False,
            "emotion": "neutral",
            "chat": "",
            "music": "",
            "button": "開始對話",
            "auto_mode": True,
        }
        self._event_bus.on(Events.AUDIO_CODEC_CHANGED, self._on_audio_codec)

    async def start(self, mode: str = "gui") -> None:
        del mode
        self._host = GodotHost.get()
        self._host.subscribe(self._on_message)
        await self._host.ensure("main")
        self._running = True
        self._host.send(self._state)
        self._push_discord_config()
        logger.info("Godot 主畫面已接上")

    async def close(self) -> None:
        self._running = False
        self._event_bus.off(Events.AUDIO_CODEC_CHANGED, self._on_audio_codec)
        self._unbind_codec()
        if self._host is not None:
            self._host.unsubscribe(self._on_message)
            await self._host.stop()
            self._host = None

    def set_status(self, status: str, connected: bool = True) -> None:
        speaking = "說話" in status
        if self._was_speaking and not speaking:
            self._flush_discord_tts()
        self._was_speaking = speaking
        self._state["status"] = status
        self._state["connected"] = connected
        self._push()

    def set_emotion(self, emotion: str) -> None:
        self._state["emotion"] = emotion
        self._push()

    def set_chat_text(self, text: str) -> None:
        self._state["chat"] = text
        self._push()

    def set_music_line(self, text: str) -> None:
        self._state["music"] = text
        self._push()

    def set_button_text(self, text: str) -> None:
        self._state["button"] = text
        self._push()

    def set_auto_mode(self, auto_mode: bool) -> None:
        self._auto_mode = auto_mode
        self._state["auto_mode"] = auto_mode
        self._push()

    def is_auto_mode(self) -> bool:
        return self._auto_mode

    def _push(self) -> None:
        if self._host is not None and self._running:
            self._host.send(self._state)

    def _on_message(self, message: dict) -> None:
        if self._tasks is None:
            return
        kind = message.get("type")
        event = {
            "manual_toggle": Events.UI_MANUAL_TOGGLE,
            "auto_toggle": Events.UI_AUTO_TOGGLE,
            "auto_start": Events.UI_AUTO_START,
            "abort": Events.UI_ABORT_REQUEST,
            "reconnect": Events.PROTOCOL_RECONNECT_REQUEST,
            "quit": Events.UI_QUIT_REQUEST,
        }.get(kind)
        if event:
            self._tasks.spawn(self._event_bus.emit(event), name=f"godot:{kind}")
            return
        if kind == "send_text":
            text = str(message.get("text", "")).strip()
            if text:
                self._tasks.spawn(
                    self._event_bus.emit(
                        Events.UI_SEND_TEXT, UISendTextRequest(text=text)
                    ),
                    name="godot:send_text",
                )
            return
        if kind == "open_settings":
            self._send_settings()
            return
        if kind == "save_settings":
            self._save_settings(message.get("data") or {})
            return
        if kind == "discord_toggle":
            self._toggle_discord()
            return
        if kind == "discord_wav":
            self._tasks.spawn(
                self._event_bus.emit(Events.DISCORD_WAV, message),
                name="godot:discord_wav",
            )

    async def _on_audio_codec(self, codec=None) -> None:
        self._unbind_codec()
        if codec is None:
            return
        adder = getattr(codec, "add_tts_pcm_listener", None)
        if not callable(adder):
            return
        adder(self._on_tts_pcm)
        self._codec = codec

    def _unbind_codec(self) -> None:
        codec = self._codec
        self._codec = None
        if codec is None:
            return
        remover = getattr(codec, "remove_tts_pcm_listener", None)
        if callable(remover):
            remover(self._on_tts_pcm)

    def _on_tts_pcm(self, pcm) -> None:
        if self._discord_on and getattr(pcm, "size", 0):
            import numpy as np

            self._tts_chunks.append(np.array(pcm, dtype=np.float32, copy=True))
        now = time.monotonic()
        if now - self._mouth_at < 0.05 or self._host is None:
            return
        self._mouth_at = now
        if pcm.size == 0:
            level = 0.0
        else:
            import numpy as np

            rms = float(np.sqrt(np.mean(np.square(pcm))))
            level = min(1.0, max(0.0, rms * 8.0))
        self._host.send({"type": "mouth", "level": level})

    def _send_settings(self) -> None:
        from src.ui.godot.settings_store import snapshot

        if self._host is not None:
            self._host.send({"type": "settings", "data": snapshot()})

    def _save_settings(self, data: dict) -> None:
        from src.ui.godot.settings_store import apply

        discord = apply(data)
        self._discord_on = bool(discord.get("discord_enabled"))
        if self._tasks is not None:
            self._tasks.spawn(
                self._event_bus.emit(Events.CONFIG_CHANGED),
                name="godot:config_changed",
            )
        if self._host is not None:
            self._host.send({"type": "settings_saved", "ok": True})
            self._host.send({"type": "discord_config", **discord})

    def _toggle_discord(self) -> None:
        from src.utils.config_manager import get_config

        cfg = get_config()
        enabled = not bool(cfg.get_config("DISCORD.ENABLED", False))
        cfg.update_config("DISCORD.ENABLED", enabled)
        self._discord_on = enabled
        self._push_discord_config()

    def _push_discord_config(self) -> None:
        from src.utils.config_manager import get_config

        try:
            cfg = get_config()
        except Exception:
            return
        enabled = bool(cfg.get_config("DISCORD.ENABLED", False))
        self._discord_on = enabled
        if self._host is None:
            return
        self._host.send(
            {
                "type": "discord_config",
                "enabled": enabled,
                "token": cfg.get_config("DISCORD.BOT_TOKEN", "") or "",
                "url": cfg.get_config("DISCORD.URL", "ws://127.0.0.1:8765")
                or "ws://127.0.0.1:8765",
            }
        )

    def _flush_discord_tts(self) -> None:
        chunks = self._tts_chunks
        self._tts_chunks = []
        if not chunks or self._host is None:
            return
        import numpy as np

        from src.constants.constants import AudioConfig
        from src.ui.godot.discord_audio import encode_wav_b64

        pcm = np.concatenate(chunks)
        if pcm.size < 160:
            return
        AudioConfig.reload()
        self._host.send(
            {
                "type": "discord_speak",
                "wav_b64": encode_wav_b64(pcm, AudioConfig.OUTPUT_SAMPLE_RATE),
            }
        )
