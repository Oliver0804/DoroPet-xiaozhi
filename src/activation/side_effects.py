"""激活验证码副作用：剪贴板与语音播报."""

from __future__ import annotations

from src.logging import get_logger

logger = get_logger()


def apply_code_side_effects(code: str, message: str | None = None) -> None:
    """日志 + 剪贴板 + 播报；不负责 CLI/GUI 文案."""
    if not code:
        return
    msg = message or "請到控制台輸入驗證碼"
    logger.info(f"激活提示: {msg}")
    logger.info(f"验证码: {code}")

    text = f".請到控制台新增裝置，輸入驗證碼：{' '.join(code)}..."
    try:
        from src.utils.common_utils import handle_verification_code

        handle_verification_code(text)
    except Exception as e:
        logger.debug(f"复制验证码失败: {e}")

    try:
        from src.utils.activation_announcer import announce_activation_code

        announce_activation_code(code, locale="zh-TW")
    except Exception as e:
        logger.debug(f"验证码播报失败: {e}")


def announce_code(code: str) -> None:
    """仅播报（轮询重试时用）."""
    if not code:
        return
    from src.utils.activation_announcer import announce_activation_code

    announce_activation_code(code, locale="zh-TW")
