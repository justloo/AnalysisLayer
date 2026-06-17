"""Mode four: synthetic scenario simulation (PRD Section 7.4).

The core of the rig and where most failure-mode testing lives. The operator
authors ground truth and declares the signal stream such a world would emit. The
harness injects the stream into the pipeline exactly as collection would, runs
the full pipeline, and checks the things that matter:

  - did the engine reach the right leading hypothesis;
  - did it catch the weak signal rather than burying it (R5);
  - did it resist the deception (A4.4);
  - did its confidence track evidence quality rather than volume.

Ground truth (the true state, the resolution, and per-signal roles) is used only
for scoring here, never fed to the pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from analysis_layer.config import Settings
from analysis_layer.models.client import ModelClient
from analysis_layer.pipeline.orchestrator import Orchestrator
from analysis_layer.schema.assessment import (
    Assessment,
    ConfidenceLevel,
    RedTeamOutcome,
)
from analysis_layer.schema.signals import Scenario, SignalRole


@dataclass
class SyntheticResult:
    scenario_id: str
    assessment: Assessment
    leading_hypothesis: str
    expected_leading: str
    released: bool  # red team did not return the event for collection
    leading_correct: bool
    must_catch_weak_signal: bool
    weak_signal_caught: Optional[bool]
    must_resist_deception: bool
    deception_resisted: Optional[bool]
    confidence_tracks_quality: bool
    notes: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        checks = [self.confidence_tracks_quality]
        if self.released:
            checks.append(self.leading_correct)
        if self.must_catch_weak_signal:
            checks.append(bool(self.weak_signal_caught))
        if self.must_resist_deception:
            checks.append(bool(self.deception_resisted))
        return all(checks)


def run_scenario(
    scenario: Scenario,
    client: Optional[ModelClient] = None,
    settings: Optional[Settings] = None,
) -> SyntheticResult:
    orch = Orchestrator(client=client, settings=settings)
    # The pipeline sees only the signal stream, never the ground truth.
    assessment = orch.analyze(
        scenario.ordered_signals(), scenario.pir, event_id=scenario.id, decision_type=scenario.decision_type
    )

    leading = assessment.leading_hypothesis()
    leading_id = leading.id if leading else "no_change"
    released = assessment.red_team.outcome != RedTeamOutcome.returned_for_collection
    notes: List[str] = []

    leading_correct = leading_id == scenario.expectations.leading_hypothesis

    weak_caught = None
    if scenario.expectations.must_catch_weak_signal:
        weak_caught = _weak_signal_caught(scenario, assessment, notes)

    deception_resisted = None
    if scenario.expectations.must_resist_deception:
        deception_resisted = _deception_resisted(scenario, assessment, leading_id, notes)

    confidence_ok = _confidence_tracks_quality(assessment, notes)

    return SyntheticResult(
        scenario_id=scenario.id,
        assessment=assessment,
        leading_hypothesis=leading_id,
        expected_leading=scenario.expectations.leading_hypothesis,
        released=released,
        leading_correct=leading_correct,
        must_catch_weak_signal=scenario.expectations.must_catch_weak_signal,
        weak_signal_caught=weak_caught,
        must_resist_deception=scenario.expectations.must_resist_deception,
        deception_resisted=deception_resisted,
        confidence_tracks_quality=confidence_ok,
        notes=notes,
    )


def _weak_signal_caught(scenario: Scenario, assessment: Assessment, notes: List[str]) -> bool:
    weak_ids = {s.id for s in scenario.signal_stream if s.role == SignalRole.weak_signal}
    if not weak_ids:
        return True
    for wid in weak_ids:
        ev = next((e for e in assessment.evidence if e.id == wid), None)
        if ev is None:
            notes.append(f"weak signal {wid} missing from evidence (dropped).")
            return False
        if not ev.weak_signal:
            notes.append(f"weak signal {wid} was not flagged/escalated (buried).")
            return False
    # It must also be surfaced as a collection gap or watch item, not silently held.
    escalated = bool(assessment.gaps) or bool(assessment.indicators_watch)
    if not escalated:
        notes.append("weak signal flagged but not escalated to gaps/watch.")
    return escalated


def _deception_resisted(
    scenario: Scenario, assessment: Assessment, leading_id: str, notes: List[str]
) -> bool:
    deception_targets = {
        s.supports for s in scenario.signal_stream if s.role == SignalRole.deception and s.supports
    }
    blocked = assessment.red_team.outcome != RedTeamOutcome.passed
    flagged = any("deception" in c.lower() for c in assessment.red_team.challenges_raised)
    not_fooled = leading_id not in deception_targets
    resisted = blocked or flagged or not_fooled
    if not resisted:
        notes.append(
            f"deception not resisted: leading={leading_id} matches planted target, red team passed."
        )
    return resisted


def _confidence_tracks_quality(assessment: Assessment, notes: List[str]) -> bool:
    """Confidence must reflect evidence quality, not volume: high confidence
    requires at least two independent corroborating origins (echo does not
    count)."""
    if assessment.confidence.level != ConfidenceLevel.high:
        return True
    leading = assessment.leading_hypothesis()
    if leading is None:
        return True
    origins = {
        e.origin_id
        for e in assessment.evidence
        if e.diagnostic_value > 0
    }
    if len(origins) < 2:
        notes.append("high confidence on a single independent origin (volume, not quality).")
        return False
    return True
