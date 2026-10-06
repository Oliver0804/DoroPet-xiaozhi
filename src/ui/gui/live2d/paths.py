"""解析 Live2D 模型路径.

优先顺序：配置 ``LIVE2D.MODEL_PATH``、环境变量 ``XIAOZHI_LIVE2D_MODEL``、
``assets/live2d/**/*.model3.json``，最后才是本机 DoroPet 的 Doro 模型.
"""

from __future__ import annotations

import os
from pathlib import Path

# 使用者自己的桌宠模型。仓库里不打包这份素材.
DORO_MODEL = Path("/Users/oliver/code/game/DoroPet/assets/doro/Doro.model3.json")


def resolve_live2d_model(
    configured: str | None = None,
    assets_dir: Path | None = None,
    *,
    env: str | None = None,
) -> Path | None:
    """返回第一个存在的 ``*.model3.json``."""
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    if env is None:
        env = os.environ.get("XIAOZHI_LIVE2D_MODEL", "")
    if env:
        candidates.append(Path(env).expanduser())
    if assets_dir is not None:
        live_dir = assets_dir / "live2d"
        if live_dir.is_dir():
            candidates.extend(sorted(live_dir.rglob("*.model3.json")))
    candidates.append(DORO_MODEL)
    for path in candidates:
        if path.is_file():
            return path
    return None
