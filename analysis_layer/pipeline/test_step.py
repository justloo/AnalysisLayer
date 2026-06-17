"""FR-6, Hypothesis testing and updating (PRD A3.6, A6).

Reach the leading judgment by elimination: the surviving hypothesis is the one
with the least diagnostic evidence against it (R9), reached by disconfirmation
rather than by accumulating support. Updating starts from base rates (the
outside view) and moves in proportion to diagnostic weight, a lot but not too
much (R10). Non-diagnostic evidence does not move the judgment (R8/R11).

Mechanics: only diagnostic *inconsistency* penalizes a hypothesis (pure
disconfirmation; confirmation does not inflate a hypothesis). The posterior is
the base rate decayed by the diagnostic evidence against each hypothesis, then
normalized. Rejected alternatives are retained and ranked with reasons.
"""
from __future__ import annotations

import math
from typing import Dict

from analysis_layer.config import Settings, get_settings
from analysis_layer.pipeline import scales
from analysis_layer.schema.assessment import HypothesisStatus
from analysis_layer.schema.state import AnalysisState, MatrixJudgment

# How sharply diagnostic evidence-against decays a hypothesis's prior. Tuned so
# updating is proportional, not explosive (R10: a lot, but not too much).
_UPDATE_K = 2.5
# A live alternative must retain at least this share of the leading posterior;
# below it the hypothesis is marked rejected (but kept, with its reason, R9).
_LIVE_ALTERNATIVE_FLOOR = 0.5


def run_test_step(state: AnalysisState, settings: Settings | None = None) -> AnalysisState:
    settings = settings or get_settings()
    evidence_against = _evidence_against(state)

    base = _base_rates_for(state, settings)
    posteriors: Dict[str, float] = {}
    for h in state.hypotheses:
        prior = base.get(h.id, 1.0 / max(len(state.hypotheses), 1))
        posteriors[h.id] = prior * math.exp(-_UPDATE_K * evidence_against.get(h.id, 0.0))

    total = sum(posteriors.values()) or 1.0
    posteriors = {k: v / total for k, v in posteriors.items()}

    leading_id = max(posteriors, key=posteriors.get)
    state.posteriors = posteriors
    state.evidence_against = evidence_against
    state.leading_hypothesis_id = leading_id

    leading_p = posteriors[leading_id]
    for h in state.hypotheses:
        h.relative_likelihood = round(posteriors[h.id], 4)
        if h.id == leading_id:
            h.status = HypothesisStatus.leading
            h.rationale = (
                f"Least diagnostic evidence against it ({evidence_against.get(h.id, 0.0):.2f}); "
                f"highest posterior after base-rate updating ({leading_p:.2f})."
            )
        elif leading_p > 0 and posteriors[h.id] >= _LIVE_ALTERNATIVE_FLOOR * leading_p:
            h.status = HypothesisStatus.live_alternative
            h.rationale = (
                f"Remains live: posterior {posteriors[h.id]:.2f} with "
                f"{evidence_against.get(h.id, 0.0):.2f} diagnostic evidence against."
            )
        else:
            h.status = HypothesisStatus.rejected
            h.rationale = (
                f"Set aside: {evidence_against.get(h.id, 0.0):.2f} diagnostic evidence against; "
                f"posterior {posteriors[h.id]:.2f}."
            )
    return state


def _evidence_against(state: AnalysisState) -> Dict[str, float]:
    """Diagnostic, grade-weighted evidence inconsistent with each hypothesis.

    Relays are collapsed to their origin (R6): many echoes of one origin count
    once, taking that origin's strongest diagnostic contribution, so volume never
    substitutes for independent corroboration (R8/R11)."""
    by_origin: Dict[tuple, float] = {}
    for cell in state.matrix:
        if cell.judgment != MatrixJudgment.inconsistent:
            continue
        e = state.evidence_by_id(cell.evidence_id)
        if e is None or e.diagnostic_value <= 0:
            continue
        weight = scales.grade_weight(e.source_reliability, e.information_credibility)
        contribution = e.diagnostic_value * weight
        key = (cell.hypothesis_id, e.origin_id)
        by_origin[key] = max(by_origin.get(key, 0.0), contribution)

    against: Dict[str, float] = {h.id: 0.0 for h in state.hypotheses}
    for (hypothesis_id, _origin), contribution in by_origin.items():
        against[hypothesis_id] = against.get(hypothesis_id, 0.0) + contribution
    return {k: round(v, 4) for k, v in against.items()}


def _base_rates_for(state: AnalysisState, settings: Settings) -> Dict[str, float]:
    """Base rates for the hypotheses actually present, renormalized (A6)."""
    present = {h.id for h in state.hypotheses}
    raw = {hid: settings.base_rates.get(hid, 0.1) for hid in present}
    total = sum(raw.values()) or 1.0
    return {hid: v / total for hid, v in raw.items()}


def hypothesis_margin(state: AnalysisState) -> float:
    """Gap between the leading and next-best posterior (A8 factor three)."""
    if not state.posteriors:
        return 0.0
    ordered = sorted(state.posteriors.values(), reverse=True)
    if len(ordered) == 1:
        return ordered[0]
    return round(ordered[0] - ordered[1], 4)
