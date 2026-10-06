"""Godot 介面協議：一行一則 JSON."""

from src.ui.godot.protocol import decode_messages, encode_message


def test_roundtrip_traditional_text():
    raw = encode_message({"type": "state", "status": "聆聽中…", "chat": "你好"})
    messages, rest = decode_messages(raw)
    assert rest == b""
    assert messages == [{"type": "state", "status": "聆聽中…", "chat": "你好"}]


def test_partial_line_stays_buffered():
    raw = encode_message({"type": "mouth", "level": 0.5})
    messages, rest = decode_messages(raw[:-4])
    assert messages == []
    assert rest
    messages, rest = decode_messages(rest + raw[-4:])
    assert messages[0]["level"] == 0.5
    assert rest == b""
