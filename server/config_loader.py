"""Config loader — reads config/game.yaml and provides typed access."""

import os
import yaml
from typing import Any

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "game.yaml",
)


def load_config(path: str | None = None) -> dict[str, Any]:
    """Load and return the game configuration dictionary."""
    cfg_path = path or _CONFIG_PATH
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    _validate(config)
    return config


def _validate(cfg: dict) -> None:
    """Basic validation of required keys."""
    required_top = [
        "passive_regen", "focus_bonus", "base_penalty", "per_sign_penalty",
        "max_buffer_length", "max_buffs", "max_debuffs", "player", "jutsu",
        "shadow_clone",
    ]
    for key in required_top:
        if key not in cfg:
            raise ValueError(f"Missing required config key: {key}")

    for i, jutsu in enumerate(cfg["jutsu"]):
        for field in [
            "name", "sign_sequence", "type", "dmg_to_enemy", "dmg_to_self",
            "chakra_cost_self", "chakra_cost_enemy", "miss_rate", "cooldown_turns",
        ]:
            if field not in jutsu:
                raise ValueError(
                    f"Jutsu index {i} ({jutsu.get('name', '?')}) missing field: {field}"
                )
