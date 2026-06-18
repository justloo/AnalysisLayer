"""FR-9, Confidence computation (PRD A3.9, A8).

Confidence is computed, not asserted, from five explicit factors and is always
expandable into its drivers (R15, R19). The combination is conservative: a
single severe weakness caps the rating low, because confidence reflects the
weakest link in the reasoning, not the average. The red team can additionally
cap it low (R16).

The five factors (A8): evidence grade, independent corroboration, hypothesis
margin, assumption fragility, and coverage of the question.
"""
from __future__ import annotations

from typing import Optional

from analysis_layer.config import ConfidenceWeights, Settings, get_settings
from analysis_layer.pipeline import scales
from analysis_layer.pipeline.test_step import hypothesis_margin
from analysis_layer.pipeline.weight import (
    collapsed_diagnostic_items,
    independent_corroboration_for,
)
from analysis_layer.schema.assessment import (
    Band,
    Confidence,
    ConfidenceDrivers,
    ConfidenceLevel,
)
from analysis_layer.schema.state import AnalysisState, MatrixJudgment

_LEVEL_BANDS = {
    ConfidenceLevel.low: Band(low=0.0, high=0.4),
    ConfidenceLevel.moderate: Band(low=0.4, high=0.7),
    ConfidenceLevel.high: Band(low=0.7, high=1.0),
}


def compute_confidence(state: AnalysisState, settings: Optional[Settings] = None) -> AnalysisState:
    settings = settings or get_settings()
    w = settings.confidence_weights
    drivers = ConfidenceDrivers(
        evidence_grade=_evidence_grade(state),
        independent_corroboration=_corroboration_factor(state),
        hypothesis_margin=hypothesis_margin(state),
        assumption_fragility=_assumption_factor(state),
        question_coverage=_coverage_factor(state),
    )
    score, level = _combine(drivers, w, cap_low=state.confidence_cap_low)
    band = _LEVEL_BANDS[level]
    state.confidence = Confidence(level=level, band=band, drivers=drivers)
    # Stash the scalar for calibration without polluting the schema.
    state.posteriors.setdefault("_confidence_score", score)
    return state


def _evidence_grade(state: AnalysisState) -> float:
    """Diagnostic-weighted aggregate grade of the evidence (A8 factor one),
    computed over origin-collapsed items so echo volume cannot inflate it (R6).

    F3: when every piece of diagnostic evidence falls below a quality floor,
    the aggregate is capped by the best individual grade weight. Volume of
    uniformly poor sources cannot substitute for a single well-graded one."""
    num = den = 0.0
    best_gw = 0.0
    for e in collapsed_diagnostic_items(state):
        gw = scales.grade_weight(e.source_reliability, e.information_credibility)
        best_gw = max(best_gw, gw)
        num += e.diagnostic_value * gw
        den += e.diagnostic_value
    if den == 0:
        return 0.15  # no diagnostic evidence => thin base, caps confidence low
    aggregate = round(num / den, 4)
    # F3: if the best individual grade weight is below the quality floor,
    # cap the aggregate so uniformly poor evidence can't reach moderate+.
    _QUALITY_FLOOR = 0.55
    if best_gw < _QUALITY_FLOOR:
        aggregate = min(aggregate, best_gw)
    return aggregate


def _corroboration_factor(state: AnalysisState) -> float:
    """Independent origins supporting the leading judgment, after relay collapse
    (A8 factor two). Echo does not count (R6).

    F3: corroboration credit is halved when the best evidence grade weight is
    below the quality floor, because agreement among uniformly weak sources is
    qualitatively different from agreement among well-graded ones."""
    leading = state.leading_hypothesis_id
    if leading is None:
        return 0.0
    count = independent_corroboration_for(state, leading)
    raw = {0: 0.1, 1: 0.4, 2: 0.7}.get(count, 1.0)
    # F3: dampen corroboration credit when all evidence is low-grade
    _QUALITY_FLOOR = 0.55
    best_gw = 0.0
    for e in collapsed_diagnostic_items(state):
        gw = scales.grade_weight(e.source_reliability, e.information_credibility)
        best_gw = max(best_gw, gw)
    if best_gw < _QUALITY_FLOOR:
        raw = raw * 0.5
    return round(raw, 4)


def _assumption_factor(state: AnalysisState) -> float:
    """High when assumptions are robust; low when a load-bearing assumption is
    fragile (A8 factor four)."""
    if not state.assumptions:
        return 0.6
    worst = max(a.fragility for a in state.assumptions)
    return round(1.0 - worst, 4)


def _coverage_factor(state: AnalysisState) -> float:
    """How much of what should be known is known (A8 factor five). Open gaps and
    unresolved weak signals lower coverage.

    F7: also penalize thin evidence streams (≤2 diagnostic items after relay
    collapse). A thin stream means the question is poorly covered regardless
    of whether explicit gaps have been named."""
    coverage = 1.0 - 0.18 * len(state.gaps)
    # F7: thin evidence stream penalty
    diagnostic_count = sum(1 for e in collapsed_diagnostic_items(state)
                           if e.diagnostic_value > 0)
    if diagnostic_count <= 2:
        coverage = min(coverage, 0.3)  # hard-cap: thin stream = poor coverage
    return round(max(0.2, min(1.0, coverage)), 4)


def _combine(drivers: ConfidenceDrivers, w: ConfidenceWeights, cap_low: bool):
    factors = {
        "evidence_grade": drivers.evidence_grade,
        "independent_corroboration": drivers.independent_corroboration,
        "hypothesis_margin": drivers.hypothesis_margin,
        "assumption_fragility": drivers.assumption_fragility,
        "question_coverage": drivers.question_coverage,
    }
    weights = {
        "evidence_grade": w.evidence_grade,
        "independent_corroboration": w.independent_corroboration,
        "hypothesis_margin": w.hypothesis_margin,
        "assumption_fragility": w.assumption_fragility,
        "question_coverage": w.question_coverage,
    }
    weighted_mean = sum(factors[k] * weights[k] for k in factors) / (sum(weights.values()) or 1.0)
    weakest = min(factors.values())

    # Weakest-link cap (R15) and red-team authority (R16).
    if cap_low or weakest <= w.severe_weakness_threshold:
        return round(min(weakest, weighted_mean), 4), ConfidenceLevel.low

    score = w.weakest_link_share * weakest + (1.0 - w.weakest_link_share) * weighted_mean
    score = round(score, 4)
    if score < 0.4:
        level = ConfidenceLevel.low
    elif score < 0.7:
        level = ConfidenceLevel.moderate
    else:
        level = ConfidenceLevel.high
    return score, level
