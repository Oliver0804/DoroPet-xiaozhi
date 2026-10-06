"""小智平台情绪名 → Doro Live2D 表情.

对照 DoroPet ``scripts/pet.gd`` 的 EMOTION_MAP：
Exp1 生气、Exp2 无言、Exp3 惊讶、Exp4 疑问、Exp5 酷、
Exp6 礼物、Exp7 读取中、Exp8 开心、TongueOut 吐舌、Highlight OFF 失神.
"""

# 空字符串表示回到默认脸（ResetExpression）
_XIAOZHI_TO_EXPRESSION: dict[str, str] = {
    "neutral": "",
    "relaxed": "",
    "angry": "Exp1",
    "confused": "Exp2",
    "sad": "Exp2",
    "crying": "Exp2",
    "embarrassed": "Exp2",
    "surprised": "Exp3",
    "shocked": "Exp3",
    "thinking": "Exp7",
    "cool": "Exp5",
    "confident": "Exp5",
    "winking": "Exp5",
    "loving": "Exp6",
    "kissy": "Exp6",
    "happy": "Exp8",
    "laughing": "Exp8",
    "funny": "TongueOut",
    "silly": "TongueOut",
    "delicious": "TongueOut",
    "sleepy": "Highlight OFF",
}

THINKING_EMOTIONS = frozenset({"thinking"})


def expression_for_emotion(name: str) -> str | None:
    """把平台情绪转成模型表情 id.

    Returns:
        表情 id；``""`` 表示恢复默认脸；``None`` 表示不认识、保持现状.
    """
    key = (name or "").strip().lower()
    if not key:
        return None
    return _XIAOZHI_TO_EXPRESSION.get(key)
