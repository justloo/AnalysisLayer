"""Model tier routing (PRD Section 9.2).

A strong reasoning tier handles low-volume, high-stakes judgment (hypothesis
generation, the red team, synthesis). A small fast tier handles the high-volume
per-cell consistency judgments and clustering, since per-event cost compounds.
Which concrete model backs each tier is config, not code.
"""
from __future__ import annotations

from enum import Enum

from analysis_layer.config import Settings


class Tier(str, Enum):
    strong = "strong"
    fast = "fast"


def model_for_tier(tier: Tier, settings: Settings) -> str:
    return settings.strong_model if tier == Tier.strong else settings.fast_model
