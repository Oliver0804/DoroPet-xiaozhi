"""TTS PCM → 嘴型开合.

DoroPet 用频谱 80–1200Hz 的幅度乘 36。这里输入的是即将播出的
单声道 float32，语速 RMS 大约 0.02–0.15，乘 8 后落在 0–1.
"""

from __future__ import annotations

import math
import threading
import time

import numpy as np

# 大约让正常说话的 RMS 顶到 1
RMS_GAIN = 8.0
# 没新样本就闭嘴，避免尾音把嘴撑住
HOLD_SECONDS = 0.08


class MouthMeter:
    """音频线程写、界面线程读的嘴型电平."""

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._level = 0.0
        self._updated = 0.0

    def push(self, pcm: np.ndarray) -> None:
        if pcm.size == 0:
            return
        rms = float(math.sqrt(float(np.mean(np.square(pcm)))))
        level = min(1.0, max(0.0, rms * RMS_GAIN))
        now = self._clock()
        with self._lock:
            self._level = level
            self._updated = now

    def level(self) -> float:
        now = self._clock()
        with self._lock:
            if now - self._updated > HOLD_SECONDS:
                return 0.0
            return self._level
