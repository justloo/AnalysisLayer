"""FR-6, Hypothesis testing and updating (PRD A3.6, A6).

Reach the leading judgment via grade-weighted net diagnosticity: for each
hypothesis, compute the balance of diagnostic evidence *for* vs *against* it,
weighted by Admiralty grade (R4, R8). Updating starts from base rates (the
outside view) and moves in proportion to net diagnostic weight, a lot but not
too much (R10). Non-diagnostic evidence does not move the judgment (R8/R11).

Mechanics (F1 fix): the posterior is the base rate shifted by the net balance
of grade-weighted diagnostic evidence (for minus against), then normalized.
Weak-unanimity collapse (F1/F3): when every supporting origin is low-grade,
only the single strongest origin counts toward evidence_for — agreement among
weak sources must not substitute for strength. Weak-signal integration (F6):
flagged weak signals score from reliability, not corroboration-crushed credibility.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple

from analysis_layer.config import Settings, get_settings
from analysis_layer.evidence_bearing import describes_deception_operation
from analysis_layer.pipeline import scales
from analysis_layer.schema.assessment import HypothesisStatus
from analysis_layer.schema.state import AnalysisState, MatrixJudgment

# How sharply net diagnosticity moves the posterior. Saturated via tanh (F8) so
# volume cannot drive posteriors to the boundary.
_UPDATE_K = 2.5
_LIVE_ALTERNATIVE_FLOOR = 0.5
# Cromwell's Rule (F8): no hypothesis may reach literal 0 or 1.
_CROMWELL_FLOOR = 0.005


def run_test_step(state: AnalysisState, settings: Settings | None = None) -> AnalysisState:
    settings = settings or get_settings()
    evidence_against = _evidence_against(state)
    evidence_for = _evidence_for(state)

    base = _base_rates_for(state, settings)
    update_k = settings.update_k if settings.update_k is not None else _UPDATE_K
    posteriors: Dict[str, float] = {}
    for h in state.hypotheses:
        prior = base.get(h.id, 1.0 / max(len(state.hypotheses), 1))
        net = evidence_for.get(h.id, 0.0) - evidence_against.get(h.id, 0.0)
        posteriors[h.id] = prior * math.exp(update_k * math.tanh(net))

    total = sum(posteriors.values()) or 1.0
    posteriors = {k: v / total for k, v in posteriors.items()}

    posteriors = {
        k: max(_CROMWELL_FLOOR, min(1.0 - _CROMWELL_FLOOR, v)) for k, v in posteriors.items()
    }
    posteriors = _apply_null_guard(state, posteriors, evidence_for)
    posteriors = _apply_deception_confirmation(state, posteriors, evidence_for)
    total = sum(posteriors.values()) or 1.0
    posteriors = {k: v / total for k, v in posteriors.items()}

    leading_id = max(posteriors, key=posteriors.get)
    state.posteriors = posteriors
    state.evidence_against = evidence_against
    state.evidence_for = evidence_for
    state.leading_hypothesis_id = leading_id

    leading_p = posteriors[leading_id]
    for h in state.hypotheses:
        net_h = evidence_for.get(h.id, 0.0) - evidence_against.get(h.id, 0.0)
        h.relative_likelihood = round(posteriors[h.id], 4)
        if h.id == leading_id:
            h.status = HypothesisStatus.leading
            h.rationale = (
                f"Highest net diagnosticity ({net_h:+.2f} = "
                f"{evidence_for.get(h.id, 0.0):.2f} for, "
                f"{evidence_against.get(h.id, 0.0):.2f} against); "
                f"posterior {leading_p:.2f}."
            )
        elif leading_p > 0 and posteriors[h.id] >= _LIVE_ALTERNATIVE_FLOOR * leading_p:
            h.status = HypothesisStatus.live_alternative
            h.rationale = (
                f"Remains live: net diagnosticity {net_h:+.2f}, "
                f"posterior {posteriors[h.id]:.2f}."
            )
        else:
            h.status = HypothesisStatus.rejected
            h.rationale = (
                f"Set aside: net diagnosticity {net_h:+.2f}, "
                f"posterior {posteriors[h.id]:.2f}."
            )
    return state


def _cell_contributions(
    state: AnalysisState, judgment: MatrixJudgment
) -> Dict[str, List[Tuple[float, float]]]:
    """Per-hypothesis list of (contribution, grade_weight) from each origin."""
    by_origin: Dict[tuple, Tuple[float, float]] = {}
    for cell in state.matrix:
        if cell.judgment != judgment:
            continue
        e = state.evidence_by_id(cell.evidence_id)
        if e is None or e.diagnostic_value <= 0:
            continue
        gw = scales.scoring_weight(
            e.source_reliability, e.information_credibility, weak_signal=e.weak_signal
        )
        contribution = e.diagnostic_value * gw
        key = (cell.hypothesis_id, e.origin_id)
        prev = by_origin.get(key, (0.0, gw))
        by_origin[key] = (max(prev[0], contribution), gw)

    grouped: Dict[str, List[Tuple[float, float]]] = {}
    for (hypothesis_id, _origin), (contrib, gw) in by_origin.items():
        grouped.setdefault(hypothesis_id, []).append((contrib, gw))
    return grouped


def _aggregate_contributions(pairs: List[Tuple[float, float]], *, for_hypothesis: bool = False) -> float:
    """Sum origin contributions, with weak-unanimity collapse (F1/F3).

    When every supporting item is below the quality floor, only the single
    strongest low-grade origin counts — and `for_hypothesis` lift is dampened
    so agreement among weak sources cannot override the null (only_wrong_data)."""
    if not pairs:
        return 0.0
    if all(gw < scales.QUALITY_FLOOR for _, gw in pairs):
        val = max(c for c, _ in pairs)
        if for_hypothesis:
            val *= 0.2
        return val
    return sum(c for c, _ in pairs)


def _apply_null_guard(
    state: AnalysisState, posteriors: Dict[str, float], evidence_for: Dict[str, float]
) -> Dict[str, float]:
    """When material hypotheses are supported only by uniformly low-grade evidence,
    defend the null prior (only_wrong_data, echo inflation)."""
    material_ids = [
        h.id for h in state.hypotheses if not h.is_null and not h.is_deception
    ]
    any_high_grade_support = False
    for hid in material_ids:
        for cell in state.matrix:
            if cell.hypothesis_id != hid or cell.judgment != MatrixJudgment.consistent:
                continue
            e = state.evidence_by_id(cell.evidence_id)
            if (
                e is not None
                and e.diagnostic_value > 0
                and not scales.is_low_grade(e.source_reliability, e.information_credibility)
            ):
                any_high_grade_support = True
                break
        if any_high_grade_support:
            break

    if any_high_grade_support:
        return posteriors
    if not any(evidence_for.get(hid, 0.0) > 0 for hid in material_ids):
        return posteriors

    null = state.null_hypothesis()
    if null is None:
        return posteriors
    boosted = dict(posteriors)
    boosted[null.id] = boosted.get(null.id, 0.0) * 1.5
    return boosted


def _deception_confirmed(state: AnalysisState) -> bool:
    """Two or more reliable origins explicitly confirm a planted-feint operation."""
    origins: set[str] = set()
    for cell in state.matrix:
        if cell.hypothesis_id != "deception" or cell.judgment != MatrixJudgment.consistent:
            continue
        e = state.evidence_by_id(cell.evidence_id)
        if (
            e is not None
            and e.diagnostic_value > 0
            and describes_deception_operation(e.content)
            and scales.is_reliable(e.source_reliability)
        ):
            origins.add(e.origin_id)
    return len(origins) >= 2


def _apply_deception_confirmation(
    state: AnalysisState, posteriors: Dict[str, float], evidence_for: Dict[str, float]
) -> Dict[str, float]:
    """When deception is explicitly confirmed, it may lead over the null (Section 6)."""
    if "deception" not in posteriors or not _deception_confirmed(state):
        return posteriors
    adjusted = dict(posteriors)
    adjusted["deception"] = adjusted.get("deception", 0.0) * 3.5
    for hid in ("price_cut", "price_increase", "repackaging"):
        if hid in adjusted:
            adjusted[hid] = adjusted[hid] * 0.45
    return adjusted


def _evidence_against(state: AnalysisState) -> Dict[str, float]:
    grouped = _cell_contributions(state, MatrixJudgment.inconsistent)
    against: Dict[str, float] = {h.id: 0.0 for h in state.hypotheses}
    for hid, pairs in grouped.items():
        against[hid] = round(_aggregate_contributions(pairs, for_hypothesis=False), 4)
    return against


def _evidence_for(state: AnalysisState) -> Dict[str, float]:
    grouped = _cell_contributions(state, MatrixJudgment.consistent)
    support: Dict[str, float] = {h.id: 0.0 for h in state.hypotheses}
    for hid, pairs in grouped.items():
        support[hid] = round(_aggregate_contributions(pairs, for_hypothesis=True), 4)
    return support


def _base_rates_for(state: AnalysisState, settings: Settings) -> Dict[str, float]:
    present = {h.id for h in state.hypotheses}
    raw = {hid: settings.base_rates.get(hid, 0.1) for hid in present}
    total = sum(raw.values()) or 1.0
    return {hid: v / total for hid, v in raw.items()}


def hypothesis_margin(state: AnalysisState) -> float:
    if not state.posteriors:
        return 0.0
    ordered = sorted(state.posteriors.values(), reverse=True)
    if len(ordered) == 1:
        return ordered[0]
    return round(ordered[0] - ordered[1], 4)
