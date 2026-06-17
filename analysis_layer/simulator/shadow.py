"""Mode six: shadow (PRD Section 7.6).

Once live, the layer runs beside a human analyst or an incumbent tool WITHOUT
acting on its outputs, logging everything, before any graduated rollout. It is a
deployment mode rather than a unit of the offline harness, included in the same
testing continuum.

This implementation runs the pipeline, persists each assessment to the
calibration store as an open (un-acted-on) judgment, and optionally records a
comparison against a human/incumbent baseline call so agreement can be reviewed
later. Nothing here takes an action; it only observes and logs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from analysis_layer.calibration.scoring import source_class_of
from analysis_layer.calibration.store import CalibrationStore, MemoryStore, StoredAssessment
from analysis_layer.config import Settings
from analysis_layer.models.client import ModelClient
from analysis_layer.schema.signals import Scenario
from analysis_layer.simulator.synthetic import run_scenario


@dataclass
class ShadowObservation:
    assessment_id: str
    leading_hypothesis: str
    confidence: str
    released: bool
    baseline_call: Optional[str] = None
    agrees_with_baseline: Optional[bool] = None


def shadow_run(
    scenarios: List[Scenario],
    store: Optional[CalibrationStore] = None,
    baselines: Optional[dict] = None,
    client: Optional[ModelClient] = None,
    settings: Optional[Settings] = None,
) -> List[ShadowObservation]:
    """Run beside a baseline without acting. `baselines` maps scenario id -> the
    human/incumbent leading call, used only for logged comparison."""
    store = store or MemoryStore()
    baselines = baselines or {}
    observations: List[ShadowObservation] = []

    for sc in scenarios:
        result = run_scenario(sc, client=client, settings=settings)
        a = result.assessment
        store.save(
            StoredAssessment(
                assessment=a,
                decision_type=sc.decision_type.value,
                source_class=source_class_of(a),
                forecast_probability=a.calibration.forecast_probability,
            )
        )
        baseline = baselines.get(sc.id)
        observations.append(
            ShadowObservation(
                assessment_id=a.id,
                leading_hypothesis=result.leading_hypothesis,
                confidence=a.confidence.level.value,
                released=result.released,
                baseline_call=baseline,
                agrees_with_baseline=(
                    None if baseline is None else baseline == result.leading_hypothesis
                ),
            )
        )
    return observations
