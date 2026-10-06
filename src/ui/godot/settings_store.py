"""把原本設定頁的項目讀出來、寫回去。不經過 PySide."""

from __future__ import annotations

from src.logging import get_logger

logger = get_logger()

_SHORTCUT_LABELS = {
    "MANUAL_PRESS": "按住說話",
    "AUTO_TOGGLE": "連續對話開關",
    "ABORT": "打斷",
    "MODE_TOGGLE": "切換模式",
    "WINDOW_TOGGLE": "顯示或隱藏",
}


def snapshot() -> dict:
    from src.utils.audio_utils import list_audio_devices
    from src.utils.config_manager import get_config

    cfg = get_config()
    devices = list_audio_devices(include_virtual=True)
    shortcuts = []
    raw_shortcuts = cfg.get_config("SHORTCUTS", {}) or {}
    for key, label in _SHORTCUT_LABELS.items():
        item = raw_shortcuts.get(key) or {}
        if not isinstance(item, dict):
            continue
        shortcuts.append(
            {
                "label": label,
                "keys": f"{item.get('modifier', '')}+{item.get('key', '')}".upper(),
            }
        )
    return {
        "input_devices": [d.get("raw_name", "") for d in devices.get("input", [])],
        "output_devices": [d.get("raw_name", "") for d in devices.get("output", [])],
        "input_device": cfg.get_config("AUDIO_DEVICES.input_device_name", "") or "",
        "output_device": cfg.get_config("AUDIO_DEVICES.output_device_name", "") or "",
        "wake_word_enabled": bool(
            cfg.get_config("WAKE_WORD_OPTIONS.USE_WAKE_WORD", True)
        ),
        "wake_word": cfg.get_config("WAKE_WORD_OPTIONS.WAKE_WORD", "你好小智")
        or "你好小智",
        "aec_enabled": bool(cfg.get_config("AEC_OPTIONS.ENABLED", False)),
        "ota_url": cfg.get_config("SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL", "") or "",
        "websocket_url": cfg.get_config("SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL", "")
        or "",
        "discord_enabled": bool(cfg.get_config("DISCORD.ENABLED", False)),
        "discord_token": cfg.get_config("DISCORD.BOT_TOKEN", "") or "",
        "discord_url": cfg.get_config("DISCORD.URL", "ws://127.0.0.1:8765")
        or "ws://127.0.0.1:8765",
        "shortcuts": shortcuts,
    }


def apply(data: dict) -> dict:
    """寫入有改到的欄位，並回傳要熱重載的結果."""
    from src.utils.audio_utils import list_audio_devices
    from src.utils.config_manager import get_config

    cfg = get_config()
    devices = list_audio_devices(include_virtual=True)

    def pick(kind: str, name: str) -> None:
        if not name:
            return
        prefix = "input" if kind == "input" else "output"
        for device in devices.get(kind, []):
            if device.get("raw_name") == name or device.get("name") == name:
                cfg.update_config(
                    f"AUDIO_DEVICES.{prefix}_device_name",
                    device["raw_name"],
                    save=False,
                )
                cfg.update_config(
                    f"AUDIO_DEVICES.{prefix}_device_id", device["index"], save=False
                )
                cfg.update_config(
                    f"AUDIO_DEVICES.{prefix}_sample_rate",
                    device.get("sample_rate"),
                    save=False,
                )
                cfg.update_config(
                    f"AUDIO_DEVICES.{prefix}_channels",
                    device.get("channels"),
                    save=False,
                )
                return

    pick("input", str(data.get("input_device", "")))
    pick("output", str(data.get("output_device", "")))
    cfg.update_config(
        "WAKE_WORD_OPTIONS.USE_WAKE_WORD",
        bool(data.get("wake_word_enabled", True)),
        save=False,
    )
    wake = str(data.get("wake_word", "")).strip()
    if wake:
        cfg.update_config("WAKE_WORD_OPTIONS.WAKE_WORD", wake, save=False)
    cfg.update_config(
        "AEC_OPTIONS.ENABLED", bool(data.get("aec_enabled", False)), save=False
    )
    ota = str(data.get("ota_url", "")).strip()
    if ota:
        cfg.update_config("SYSTEM_OPTIONS.NETWORK.OTA_VERSION_URL", ota, save=False)
    cfg.update_config(
        "SYSTEM_OPTIONS.NETWORK.WEBSOCKET_URL",
        str(data.get("websocket_url", "")).strip() or None,
        save=False,
    )
    cfg.update_config(
        "DISCORD.ENABLED", bool(data.get("discord_enabled", False)), save=False
    )
    cfg.update_config(
        "DISCORD.BOT_TOKEN", str(data.get("discord_token", "")), save=False
    )
    url = str(data.get("discord_url", "")).strip() or "ws://127.0.0.1:8765"
    cfg.update_config("DISCORD.URL", url, save=False)
    cfg.save_config()
    logger.info("Godot 設定已寫入")
    return {
        "discord_enabled": bool(data.get("discord_enabled", False)),
        "discord_token": str(data.get("discord_token", "")),
        "discord_url": url,
    }
