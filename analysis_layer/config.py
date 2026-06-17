"""Configuration loader.

Settings come from environment variables (optionally a .env file). Everything
has an offline-friendly default so the harness runs with zero configuration.
The model tier names live here, not in code, so a provider/model swap never
touches the pipeline (PRD Section 9.1).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict

try:  # python-dotenv is a core dep, but stay import-safe regardless.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv missing is non-fatal
    pass


def _get(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


@dataclass(frozen=True)
class ConfidenceWeights:
    """Weights for the five-factor confidence model (PRD A8).

    The exact weighting is explicitly a tunable parameter, refined from
    calibration data rather than fixed by intuition (A8). A single severe
    weakness caps the rating low regardless of these weights (R15).
    """

    evidence_grade: float = 0.25
    independent_corroboration: float = 0.2
    hypothesis_margin: float = 0.25
    assumption_fragility: float = 0.15
    question_coverage: float = 0.15

    # Any factor at or below this hard-caps confidence to "low" (weakest link).
    severe_weakness_threshold: float = 0.34
    # Blend of the weakest factor vs. the weighted mean when no severe weakness.
    weakest_link_share: float = 0.4


@dataclass(frozen=True)
class Settings:
    model_backend: str = field(default_factory=lambda: _get("ANALYSIS_LAYER_MODEL_BACKEND", "mock"))
    # Google AI Studio / Gemini Developer API (https://aistudio.google.com/apikey).
    # The google-genai SDK also reads GEMINI_API_KEY / GOOGLE_API_KEY from the env.
    google_api_key: str = field(
        default_factory=lambda: _get("GOOGLE_API_KEY", _get("GEMINI_API_KEY", ""))
    )
    # Legacy Anthropic provider (optional alternative backend).
    anthropic_api_key: str = field(default_factory=lambda: _get("ANTHROPIC_API_KEY", ""))
    strong_model: str = field(
        default_factory=lambda: _get("ANALYSIS_LAYER_STRONG_MODEL", "gemini-2.5-pro")
    )
    fast_model: str = field(
        default_factory=lambda: _get("ANALYSIS_LAYER_FAST_MODEL", "gemini-2.5-flash")
    )
    temperature: float = field(
        default_factory=lambda: float(_get("ANALYSIS_LAYER_TEMPERATURE", "0.2"))
    )
    store_backend: str = field(default_factory=lambda: _get("ANALYSIS_LAYER_STORE_BACKEND", "memory"))
    database_url: str = field(
        default_factory=lambda: _get(
            "ANALYSIS_LAYER_DATABASE_URL",
            "postgresql://analysis:analysis@localhost:5432/analysis_layer",
        )
    )
    confidence_weights: ConfidenceWeights = field(default_factory=ConfidenceWeights)

    # Base rates (the "outside view", PRD A6) for the v0 pricing decision type.
    # Updating starts from these and moves proportionally to diagnostic weight.
    base_rates: Dict[str, float] = field(
        default_factory=lambda: {
            "price_cut": 0.18,
            "price_increase": 0.15,
            "repackaging": 0.12,
            "no_change": 0.5,
            "deception": 0.05,
        }
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings_cache() -> None:
    """Test hook: force re-read of the environment on next get_settings()."""
    global _settings
    _settings = None
