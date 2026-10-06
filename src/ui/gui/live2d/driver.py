"""Live2D 姿态驱动.

把 DoroPet ``pet.gd`` 里每帧做的事收成纯函数：视线平滑、口型 lerp、
眨眼、挑眉、思考时眼睛绕圈。渲染器只负责把返回的参数写进模型.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from src.ui.gui.live2d.emotions import THINKING_EMOTIONS, expression_for_emotion


def _clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


@dataclass
class Live2DDriver:
    """一帧一帧算出要压过动作的参数."""

    head_strength: float = 30.0
    eye_strength: float = 1.0
    body_strength: float = 10.0
    gaze_lerp: float = 6.0
    mouth_lerp: float = 20.0
    blink_duration: float = 0.18
    brow_duration: float = 0.6
    idle_after: float = 3.0
    rng: random.Random = field(default_factory=random.Random)

    thinking: bool = False
    _expression: str = ""
    _expression_dirty: bool = False
    _smooth_dx: float = 0.0
    _smooth_dy: float = 0.0
    _smooth_mouth: float = 0.0
    _thinking_t: float = 0.0
    _blink_t: float = 3.0
    _blink_anim_t: float = -1.0
    _brow_t: float = 12.0
    _brow_anim_t: float = -1.0

    def set_emotion(self, name: str) -> None:
        """接收小智 ``llm.emotion``. 未知名字不改当前表情."""
        expr = expression_for_emotion(name)
        if expr is None:
            return
        key = (name or "").strip().lower()
        self.thinking = key in THINKING_EMOTIONS
        if not self.thinking:
            self._thinking_t = 0.0
        if expr != self._expression:
            self._expression = expr
            self._expression_dirty = True

    def consume_expression(self) -> str | None:
        """取出一次表情切换. ``None`` 表示这帧不用动表情."""
        if not self._expression_dirty:
            return None
        self._expression_dirty = False
        return self._expression

    def tick(
        self,
        dt: float,
        pointer_dx: float,
        pointer_dy: float,
        pointer_idle: bool,
        idle_time: float,
        mouth_target: float,
    ) -> dict[str, float]:
        """推进一帧，返回要写入模型的参数."""
        dt = _clamp(dt, 0.0, 0.1)
        dx, dy = self._gaze_target(dt, pointer_dx, pointer_dy, pointer_idle, idle_time)
        gaze_k = _clamp(dt * self.gaze_lerp, 0.0, 1.0)
        self._smooth_dx += (dx - self._smooth_dx) * gaze_k
        self._smooth_dy += (dy - self._smooth_dy) * gaze_k

        mouth_k = _clamp(dt * self.mouth_lerp, 0.0, 1.0)
        target = _clamp(mouth_target, 0.0, 1.0)
        self._smooth_mouth += (target - self._smooth_mouth) * mouth_k

        params: dict[str, float] = {
            "ParamAngleX": self._smooth_dx * self.head_strength,
            "ParamAngleY": -self._smooth_dy * self.head_strength,
            "ParamAngleZ": self._smooth_dx * self.head_strength * 0.3,
            "ParamEyeBallX": self._smooth_dx * self.eye_strength,
            "ParamEyeBallY": -self._smooth_dy * self.eye_strength,
            "ParamBodyAngleX": self._smooth_dx * self.body_strength,
            "ParamMouthOpenY": self._smooth_mouth,
        }
        params.update(self._blink_params(dt))
        params.update(self._brow_params(dt))
        return params

    def _gaze_target(
        self,
        dt: float,
        pointer_dx: float,
        pointer_dy: float,
        pointer_idle: bool,
        idle_time: float,
    ) -> tuple[float, float]:
        if self.thinking:
            self._thinking_t += dt
            ang = self._thinking_t * 3.0
            return math.cos(ang) * 0.7, math.sin(ang) * 0.7
        if pointer_idle:
            t = max(0.0, idle_time)
            dx = math.sin(t * 0.5) * 0.6 + math.sin(t * 1.3) * 0.2
            dy = math.sin(t * 0.7) * 0.3 + math.cos(t * 1.1) * 0.2
            return dx, dy
        return _clamp(pointer_dx, -1.0, 1.0), _clamp(pointer_dy, -1.0, 1.0)

    def _blink_params(self, dt: float) -> dict[str, float]:
        if self.thinking:
            return {}
        if self._blink_anim_t >= 0.0:
            self._blink_anim_t += dt
            if self._blink_anim_t >= self.blink_duration:
                self._blink_anim_t = -1.0
                self._blink_t = self.rng.uniform(10.0, 30.0)
                return {"ParamEyeLOpen": 1.0, "ParamEyeROpen": 1.0}
            t = self._blink_anim_t / self.blink_duration
            closed = 1.0 - abs(t * 2.0 - 1.0)
            eye = 1.0 - closed
            return {"ParamEyeLOpen": eye, "ParamEyeROpen": eye}
        self._blink_t -= dt
        if self._blink_t <= 0.0:
            self._blink_anim_t = 0.0
        return {}

    def _brow_params(self, dt: float) -> dict[str, float]:
        if self.thinking:
            return {}
        if self._brow_anim_t >= 0.0:
            self._brow_anim_t += dt
            if self._brow_anim_t >= self.brow_duration:
                self._brow_anim_t = -1.0
                self._brow_t = self.rng.uniform(8.0, 20.0)
                return {"ParamBrowLY": 0.0, "ParamBrowRY": 0.0}
            t = self._brow_anim_t / self.brow_duration
            value = math.sin(t * math.pi)
            return {"ParamBrowLY": value, "ParamBrowRY": value}
        self._brow_t -= dt
        if self._brow_t <= 0.0:
            self._brow_anim_t = 0.0
        return {}
