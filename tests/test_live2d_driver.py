"""Live2D 表情映射、姿态驱动、嘴型电平。不依赖 OpenGL."""

import random

import numpy as np
import pytest

from src.ui.gui.live2d.driver import Live2DDriver
from src.ui.gui.live2d.emotions import expression_for_emotion
from src.ui.gui.live2d.mouth import MouthMeter
from src.ui.gui.live2d.paths import resolve_live2d_model


def test_expression_map_matches_doro_names():
    assert expression_for_emotion("happy") == "Exp8"
    assert expression_for_emotion("HAPPY") == "Exp8"
    assert expression_for_emotion("angry") == "Exp1"
    assert expression_for_emotion("thinking") == "Exp7"
    assert expression_for_emotion("silly") == "TongueOut"
    assert expression_for_emotion("sleepy") == "Highlight OFF"
    assert expression_for_emotion("neutral") == ""
    assert expression_for_emotion("not-a-mood") is None
    assert expression_for_emotion("") is None


def test_unknown_emotion_keeps_current_expression():
    driver = Live2DDriver()
    driver.set_emotion("happy")
    assert driver.consume_expression() == "Exp8"
    driver.set_emotion("not-a-mood")
    assert driver.consume_expression() is None
    assert not driver.thinking


def test_thinking_orbits_and_does_not_blink():
    driver = Live2DDriver(rng=random.Random(0))
    driver.set_emotion("thinking")
    assert driver.thinking
    assert driver.consume_expression() == "Exp7"
    driver._blink_t = 0.0
    first = driver.tick(0.05, 1.0, 0.0, False, 0.0, 0.0)
    second = driver.tick(0.4, 1.0, 0.0, False, 0.0, 0.0)
    assert "ParamEyeLOpen" not in first
    assert first["ParamAngleX"] != second["ParamAngleX"]


def test_mouth_and_gaze_lerp_toward_target():
    driver = Live2DDriver()
    first = driver.tick(0.01, 1.0, 0.0, False, 0.0, 1.0)
    second = driver.tick(0.01, 1.0, 0.0, False, 0.0, 1.0)
    assert 0 < first["ParamMouthOpenY"] < second["ParamMouthOpenY"] <= 1
    assert 0 < first["ParamAngleX"] < second["ParamAngleX"]
    assert first["ParamEyeBallX"] > 0


def test_blink_closes_then_reopens():
    driver = Live2DDriver(rng=random.Random(1))
    driver._blink_t = 0.0
    driver.tick(0.001, 0.0, 0.0, False, 0.0, 0.0)
    mid = driver.tick(0.09, 0.0, 0.0, False, 0.0, 0.0)
    assert mid["ParamEyeLOpen"] < 0.2
    assert mid["ParamEyeROpen"] == mid["ParamEyeLOpen"]
    opened = None
    for _ in range(10):
        opened = driver.tick(0.05, 0.0, 0.0, False, 0.0, 0.0)
        if opened.get("ParamEyeLOpen") == 1.0:
            break
    assert opened is not None
    assert opened["ParamEyeLOpen"] == 1.0


def test_idle_sway_moves_without_pointer():
    driver = Live2DDriver()
    pose = driver.tick(0.05, 0.0, 0.0, True, 1.2, 0.0)
    assert pose["ParamAngleX"] != 0 or pose["ParamAngleY"] != 0


def test_mouth_meter_gain_and_decay():
    now = [0.0]
    meter = MouthMeter(clock=lambda: now[0])
    meter.push(np.full(200, 0.1, dtype=np.float32))
    assert meter.level() == pytest.approx(0.8)
    now[0] = 1.0
    assert meter.level() == 0.0


def test_resolve_model_prefers_config_then_assets_then_env(tmp_path):
    configured = tmp_path / "picked.model3.json"
    configured.write_text("{}", encoding="utf-8")
    assert resolve_live2d_model(str(configured), tmp_path, env="") == configured

    assets = tmp_path / "bundle"
    model_dir = assets / "live2d" / "doro"
    model_dir.mkdir(parents=True)
    bundled = model_dir / "Doro.model3.json"
    bundled.write_text("{}", encoding="utf-8")
    missing = tmp_path / "missing.model3.json"
    assert resolve_live2d_model(str(missing), assets, env="") == bundled

    from_env = tmp_path / "from-env.model3.json"
    from_env.write_text("{}", encoding="utf-8")
    assert resolve_live2d_model("", None, env=str(from_env)) == from_env
