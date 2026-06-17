"""Pipeline order enforcement (PRD R3) and end-to-end completeness."""
from __future__ import annotations

import pytest

from analysis_layer.pipeline.orchestrator import STAGE_ORDER, Orchestrator, StageOrderError
from analysis_layer.schema.state import AnalysisState


def test_full_run_completes_all_stages_in_order(library):
    sc = library[0]
    orch = Orchestrator()
    orch.analyze(sc.ordered_signals(), sc.pir, event_id=sc.id)
    assert orch.last_state.stages_completed == STAGE_ORDER


def test_stage_out_of_order_is_rejected():
    orch = Orchestrator()
    state = AnalysisState(event_id="t", pir_ref="p")
    # Jumping straight to the red team without the prior stages must be refused.
    with pytest.raises(StageOrderError):
        orch._enter(state, "red_team")


def test_no_judgment_can_skip_grading_or_review(library):
    # An assessment always carries graded evidence, a hypothesis set, and a
    # red-team outcome: structurally impossible to skip a stage (R3).
    from analysis_layer.simulator.synthetic import run_scenario

    a = run_scenario(library[0]).assessment
    assert a.evidence and all(e.source_reliability for e in a.evidence)
    assert a.hypotheses
    assert a.red_team.outcome is not None
