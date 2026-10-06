"""Godot 介面跟後端之間的一行一則 JSON."""

from __future__ import annotations

import json
from typing import Any


def encode_message(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def decode_messages(buffer: bytes) -> tuple[list[dict[str, Any]], bytes]:
    """切出完整的一行。半行留在 buffer."""
    messages: list[dict[str, Any]] = []
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        text = line.decode("utf-8").strip()
        if not text:
            continue
        data = json.loads(text)
        if isinstance(data, dict):
            messages.append(data)
    return messages, buffer
