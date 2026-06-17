"""Mode one: deterministic fixtures (PRD Section 7.1).

The code nodes tested as ordinary software with fixed input and fixed output:
  - a fixed matrix yields the expected leading hypothesis;
  - a fixed factor vector yields the expected confidence band;
  - a fixed set of relays yields the expected collapsed corroboration count.
"""
from __future__ import annotations

import pytest

from analysis_layer.config import ConfidenceWeights
from analysis_layer.pipeline.confidence import _combine
from analysis_layer.pipeline.matrix import score_diagnosticity
from analysis_layer.pipeline.test_step import run_test_step
from analysis_layer.pipeline.weight import independent_corroboration_for
from analysis_layer.schema.assessment import (
    ConfidenceDrivers,
    ConfidenceLevel,
    Evidence,
    Hypothesis,
    InformationCredibility,
    SourceReliability,
    SourceType,
)
from analysis_layer.schema.state import AnalysisState, MatrixCell, MatrixJudgment

pytestmark = pytest.mark.fixtures


def _evidence(eid, origin, reliability=SourceReliability.B, credibility=InformationCredibility.two):
    return Evidence(
        id=eid,
        content=f"item {eid}",
        source_reliability=reliability,
        information_credibility=credibility,
        source_type=SourceType(primary=True, objective=True),
        origin_id=origin,
    )


def _hyps():
    return [
        Hypothesis(id="price_cut", statement="cut"),
        Hypothesis(id="price_increase", statement="increase"),
        Hypothesis(id="no_change", statement="no change", is_null=True),
    ]


def test_fixed_matrix_yields_expected_leading():
    # e1 and e2 (independent origins) point to price_cut; both are inconsistent
    # with the alternatives. price_cut should win by disconfirmation.
    state = AnalysisState(event_id="t", pir_ref="p", hypotheses=_hyps())
    state.evidence = [_evidence("e1", "o1"), _evidence("e2", "o2")]
    cells = []
    for eid in ("e1", "e2"):
        cells.append(MatrixCell(evidence_id=eid, hypothesis_id="price_cut", judgment=MatrixJudgment.consistent))
        cells.append(MatrixCell(evidence_id=eid, hypothesis_id="price_increase", judgment=MatrixJudgment.inconsistent))
        cells.append(MatrixCell(evidence_id=eid, hypothesis_id="no_change", judgment=MatrixJudgment.inconsistent))
    state.matrix = cells
    score_diagnosticity(state)

    run_test_step(state)

    assert state.leading_hypothesis_id == "price_cut"
    assert state.hypothesis("price_cut").relative_likelihood > state.hypothesis("no_change").relative_likelihood


def test_non_diagnostic_evidence_does_not_drive_conclusion():
    # An item consistent with EVERY hypothesis (vivid but non-diagnostic) must
    # not move the judgment off the base-rate leader (R8).
    state = AnalysisState(event_id="t", pir_ref="p", hypotheses=_hyps())
    state.evidence = [_evidence("e1", "o1")]
    state.matrix = [
        MatrixCell(evidence_id="e1", hypothesis_id=h.id, judgment=MatrixJudgment.consistent)
        for h in state.hypotheses
    ]
    score_diagnosticity(state)
    assert state.evidence[0].diagnostic_value == 0.0

    run_test_step(state)
    # With nothing diagnostic, the null (highest base rate) leads.
    assert state.leading_hypothesis_id == "no_change"


@pytest.mark.parametrize(
    "drivers,expected",
    [
        (dict(evidence_grade=0.9, independent_corroboration=0.9, hypothesis_margin=0.9, assumption_fragility=0.9, question_coverage=0.9), ConfidenceLevel.high),
        (dict(evidence_grade=0.55, independent_corroboration=0.55, hypothesis_margin=0.55, assumption_fragility=0.55, question_coverage=0.55), ConfidenceLevel.moderate),
        # one severe weakness caps the rating low (R15 weakest link)
        (dict(evidence_grade=0.2, independent_corroboration=0.9, hypothesis_margin=0.9, assumption_fragility=0.9, question_coverage=0.9), ConfidenceLevel.low),
    ],
)
def test_fixed_factor_vector_yields_expected_band(drivers, expected):
    _score, level = _combine(ConfidenceDrivers(**drivers), ConfidenceWeights(), cap_low=False)
    assert level == expected


def test_red_team_cap_forces_low_confidence():
    strong = ConfidenceDrivers(
        evidence_grade=0.9, independent_corroboration=0.9, hypothesis_margin=0.9,
        assumption_fragility=0.9, question_coverage=0.9,
    )
    _score, level = _combine(strong, ConfidenceWeights(), cap_low=True)
    assert level == ConfidenceLevel.low


def test_relays_collapse_to_one_corroboration_count():
    # Three items support price_cut, but two share an origin (echo). The
    # corroboration count must be 2 (distinct origins), not 3 (R6).
    state = AnalysisState(event_id="t", pir_ref="p", hypotheses=_hyps())
    state.evidence = [
        _evidence("a", "O1"),
        _evidence("a_echo", "O1"),  # echo of the same origin
        _evidence("b", "O2"),
    ]
    state.matrix = [
        MatrixCell(evidence_id=eid, hypothesis_id="price_cut", judgment=MatrixJudgment.consistent)
        for eid in ("a", "a_echo", "b")
    ] + [
        MatrixCell(evidence_id=eid, hypothesis_id="no_change", judgment=MatrixJudgment.inconsistent)
        for eid in ("a", "a_echo", "b")
    ]
    score_diagnosticity(state)

    assert independent_corroboration_for(state, "price_cut") == 2
