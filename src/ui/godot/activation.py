"""裝置啟用畫面，顯示在 Godot 裡."""

from __future__ import annotations

import asyncio

from src.logging import get_logger
from src.ui.godot.host import GodotHost
from src.ui.shared.activation import BaseActivation

logger = get_logger()


class GodotActivation(BaseActivation):
    """取到驗證碼後交給 Godot，等使用者在 xiaozhi.me 綁定."""

    def __init__(self, activation_service, init_result: dict):
        super().__init__(activation_service, init_result)
        self._done: asyncio.Future | None = None
        self._host: GodotHost | None = None

    async def run(self) -> bool:
        self._host = GodotHost.get()
        self._done = asyncio.get_running_loop().create_future()
        self._host.subscribe(self._on_message)
        try:
            await self._host.ensure("activation")
            success = await self._core_activate()
        finally:
            self._host.unsubscribe(self._on_message)
        if not success and self._host is not None:
            await self._host.stop()
        return success

    def _on_message(self, message: dict) -> None:
        kind = message.get("type")
        if kind == "quit" and self._done and not self._done.done():
            if self._service:
                self._service.cancel_activation()
            self._done.set_result(False)
        elif kind == "copy_code":
            logger.info("使用者複製了驗證碼")
        elif kind == "open_url":
            logger.info("使用者打開了啟用頁面")

    def _show_code(self, data: dict) -> None:
        if self._host is None:
            return
        info = {}
        if self._service is not None:
            info = self._service.get_device_info() or {}
        url = ""
        try:
            url = self._service.get_config_manager().get_config(
                "SYSTEM_OPTIONS.NETWORK.AUTHORIZATION_URL", "https://xiaozhi.me/"
            )
        except Exception:
            url = "https://xiaozhi.me/"
        self._host.send(
            {
                "type": "activation",
                "status": "waiting",
                "code": data.get("code", ""),
                "url": url or "https://xiaozhi.me/",
                "serial": info.get("serial_number") or "",
                "mac": info.get("mac_address") or "",
            }
        )

    def _show_result(self, success: bool) -> None:
        if self._host is None:
            return
        self._host.send(
            {
                "type": "activation",
                "status": "ok" if success else "error",
                "message": "" if success else "啟用失敗，請再試一次",
            }
        )

    def _show_error(self, msg: str) -> None:
        logger.error("啟用失敗: %s", msg)
        if self._host is not None:
            self._host.send(
                {
                    "type": "activation",
                    "status": "error",
                    "message": _zh_tw(msg),
                }
            )


def _zh_tw(msg: str) -> str:
    table = {
        "激活服务未初始化": "啟用服務還沒準備好",
        "未获取到激活数据": "沒有拿到啟用資料",
    }
    return table.get(msg, msg)
