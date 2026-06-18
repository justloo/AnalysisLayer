"""FR-12, Aggregation across model analysts (PRD A11, R18).

Running several model analysts and aggregating their judgments improves accuracy
(the wisdom-of-crowds forecasting result). Crucially, material disagreement among
them is itself a signal that confidence should be lower, and it is preserved and
surfaced rather than averaged into false consensus.

With the deterministic MockClient every analyst returns the same judgment, so
disagreement is 0; with a real, non-deterministic provider it becomes a live
confidence input.
"""
from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import replace
from typing import List, Optional

from analysis_layer.config import Settings, get_settings
from analysis_layer.models.client import ModelClient
from analysis_layer.pipeline.confidence import _LEVEL_BANDS
from analysis_layer.pipeline.orchestrator import Orchestrator
from analysis_layer.schema.assessment import Assessment, ConfidenceLevel
from analysis_layer.schema.signals import Signal

_LEVEL_ORDER = [ConfidenceLevel.high, ConfidenceLevel.moderate, ConfidenceLevel.low]


def analyze_ensemble(
    signals: List[Signal],
    pir_ref: str,
    n_analysts: int = 3,
    client: Optional[ModelClient] = None,
    settings: Optional[Settings] = None,
    settings_per_analyst: Optional[List[Settings]] = None,
    event_id: str = "event-1",
) -> Assessment:
    settings = settings or get_settings()
    if settings_per_analyst is not None:
        analyst_settings = settings_per_analyst
    else:
        analyst_settings = [settings] * max(1, n_analysts)
    runs: List[Assessment] = []
    for i in range(max(1, n_analysts)):
        orch = Orchestrator(client=client, settings=analyst_settings[min(i, len(analyst_settings) - 1)])
        runs.append(orch.analyze(signals, pir_ref, event_id=event_id))

    leading_ids = [a.leading_hypothesis().id for a in runs if a.leading_hypothesis()]
    majority_id, majority_count = Counter(leading_ids).most_common(1)[0]
    agreement = majority_count / len(runs)
    disagreement = round(1.0 - agreement, 4)

    # Representative run: a majority analyst, with averaged forecast probability.
    representative = next(
        a for a in runs if a.leading_hypothesis() and a.leading_hypothesis().id == majority_id
    )
    forecasts = [
        a.calibration.forecast_probability
        for a in runs
        if a.leading_hypothesis() and a.leading_hypothesis().id == majority_id
    ]
    representative.calibration.forecast_probability = round(statistics.fmean(forecasts), 4)
    representative.ensemble_disagreement = disagreement

    # Disagreement lowers confidence and is preserved, not averaged away (R18).
    if disagreement >= 0.34 and representative.confidence.level != ConfidenceLevel.low:
        representative.confidence = representative.confidence.model_copy(
            update={
                "level": _downgrade(representative.confidence.level),
                "band": _LEVEL_BANDS[_downgrade(representative.confidence.level)],
            }
        )
        representative.red_team.challenges_raised.append(
            f"Ensemble disagreement {disagreement:.0%}: analysts split on the leading hypothesis; "
            "confidence lowered."
        )
    return representative


def _downgrade(level: ConfidenceLevel) -> ConfidenceLevel:
    idx = _LEVEL_ORDER.index(level)
    return _LEVEL_ORDER[min(idx + 1, len(_LEVEL_ORDER) - 1)]
