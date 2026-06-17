"""The deterministic orchestrator (PRD Section 4, R3).

A fixed, ordered pipeline with model-reasoning nodes inside it. This is NOT an
autonomous agent that picks its own path; the stage order is enforced so the
engine cannot emit a judgment that skipped grading, hypothesis testing, or
adversarial review (R3). Code performs orchestration and all arithmetic; the
model performs judgment.

Stage order mirrors PRD A3:
  intake -> cluster -> grade -> weight -> hypotheses -> matrix -> test ->
  assumptions -> red team -> confidence -> likelihood -> synthesis.
"""
from __future__ import annotations

from typing import List, Optional

from analysis_layer.config import Settings, get_settings
from analysis_layer.models.client import ModelClient, build_client
from analysis_layer.pipeline import (
    assumptions,
    cluster,
    confidence,
    grade,
    hypotheses,
    intake,
    likelihood,
    matrix,
    redteam,
    synthesis,
    test_step,
    weight,
)
from analysis_layer.schema.assessment import Assessment
from analysis_layer.schema.signals import DecisionType, Signal
from analysis_layer.schema.state import AnalysisState

# The canonical, enforced order. The orchestrator records each completed stage
# and refuses to skip ahead (R3).
STAGE_ORDER = [
    "intake",
    "cluster",
    "grade",
    "weight",
    "hypotheses",
    "matrix",
    "test",
    "assumptions",
    "red_team",
    "confidence",
    "likelihood",
    "synthesis",
]


class StageOrderError(RuntimeError):
    """Raised if a stage is run out of the enforced order."""


class Orchestrator:
    def __init__(
        self,
        client: Optional[ModelClient] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or build_client(self.settings)

    def _enter(self, state: AnalysisState, stage: str) -> None:
        expected_index = len(state.stages_completed)
        if expected_index >= len(STAGE_ORDER) or STAGE_ORDER[expected_index] != stage:
            raise StageOrderError(
                f"Stage '{stage}' attempted out of order; expected "
                f"'{STAGE_ORDER[expected_index] if expected_index < len(STAGE_ORDER) else 'none'}'."
            )

    def _done(self, state: AnalysisState, stage: str) -> None:
        state.stages_completed.append(stage)

    def analyze(
        self,
        signals: List[Signal],
        pir_ref: str,
        event_id: str = "event-1",
        decision_type: DecisionType = DecisionType.competitor_pricing_move,
    ) -> Assessment:
        normalized = intake.run_intake(signals, self.client)
        state = cluster.cluster_signals(normalized, pir_ref, event_id, decision_type)
        # intake/cluster already applied; record them.
        state.stages_completed.extend(["intake", "cluster"])

        self._enter(state, "grade")
        grade.grade_event(state, self.client)
        self._done(state, "grade")

        self._enter(state, "weight")
        weight.weight_event(state)
        self._done(state, "weight")

        self._enter(state, "hypotheses")
        hypotheses.generate_hypotheses(state, self.client)
        self._done(state, "hypotheses")

        self._enter(state, "matrix")
        matrix.build_matrix(state, self.client)
        self._done(state, "matrix")

        self._enter(state, "test")
        test_step.run_test_step(state, self.settings)
        self._done(state, "test")

        self._enter(state, "assumptions")
        assumptions.check_assumptions(state, self.client)
        self._done(state, "assumptions")

        self._enter(state, "red_team")
        redteam.run_red_team(state, self.client, self.settings)
        self._done(state, "red_team")

        self._enter(state, "confidence")
        confidence.compute_confidence(state, self.settings)
        self._done(state, "confidence")

        self._enter(state, "likelihood")
        likelihood.express_likelihood(state)
        self._done(state, "likelihood")

        self._enter(state, "synthesis")
        assessment = synthesis.synthesize(state, self.client)
        self._done(state, "synthesis")

        self._last_state = state
        return assessment

    @property
    def last_state(self) -> Optional[AnalysisState]:
        return getattr(self, "_last_state", None)


def run_pipeline(
    signals: List[Signal],
    pir_ref: str,
    client: Optional[ModelClient] = None,
    settings: Optional[Settings] = None,
    event_id: str = "event-1",
) -> Assessment:
    """Convenience entry point: run the full pipeline once and return the
    assessment."""
    return Orchestrator(client=client, settings=settings).analyze(
        signals, pir_ref, event_id=event_id
    )
