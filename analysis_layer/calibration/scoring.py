"""FR-13, Calibration scoring (PRD A11).

Score every resolvable judgment with a Brier score (lower is better) and plot
stated probability against observed frequency. The Brier score decomposes into
calibration/reliability (when the layer says 70%, does it happen ~70% of the
time) and resolution (does it make decisive, differentiated calls rather than
hugging 50%). Scores are broken down per segment (decision type and source
class), because the layer may be well-calibrated on one and poorly on another
and those must be corrected independently.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from analysis_layer.calibration.store import CalibrationStore
from analysis_layer.schema.assessment import Assessment

# A (forecast_probability, outcome) pair: the probability the resolvable claim
# proved out, and whether it actually did.
Pair = Tuple[float, bool]


@dataclass
class CalibrationBin:
    lower: float
    upper: float
    count: int
    mean_forecast: float
    observed_frequency: float


@dataclass
class SegmentScore:
    segment: str
    n: int
    brier: float
    reliability: float  # lower is better (calibration error)
    resolution: float  # higher is better
    uncertainty: float
    base_rate: float
    curve: List[CalibrationBin] = field(default_factory=list)


@dataclass
class ScoreReport:
    overall: SegmentScore
    by_decision_type: Dict[str, SegmentScore] = field(default_factory=dict)
    by_source_class: Dict[str, SegmentScore] = field(default_factory=dict)


def brier_score(pairs: List[Pair]) -> float:
    if not pairs:
        return float("nan")
    return sum((p - (1.0 if o else 0.0)) ** 2 for p, o in pairs) / len(pairs)


def calibration_curve(pairs: List[Pair], n_bins: int = 10) -> List[CalibrationBin]:
    bins: List[CalibrationBin] = []
    for i in range(n_bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins
        in_bin = [
            (p, o)
            for p, o in pairs
            if (p >= lo and p < hi) or (i == n_bins - 1 and p == 1.0)
        ]
        if not in_bin:
            continue
        mean_f = sum(p for p, _ in in_bin) / len(in_bin)
        obs = sum(1 for _, o in in_bin if o) / len(in_bin)
        bins.append(
            CalibrationBin(
                lower=round(lo, 3),
                upper=round(hi, 3),
                count=len(in_bin),
                mean_forecast=round(mean_f, 4),
                observed_frequency=round(obs, 4),
            )
        )
    return bins


def score_segment(name: str, pairs: List[Pair], n_bins: int = 10) -> SegmentScore:
    n = len(pairs)
    if n == 0:
        return SegmentScore(name, 0, float("nan"), float("nan"), float("nan"), 0.0, 0.0)
    base_rate = sum(1 for _, o in pairs if o) / n
    uncertainty = base_rate * (1.0 - base_rate)
    curve = calibration_curve(pairs, n_bins)
    # Murphy decomposition: Brier = reliability - resolution + uncertainty.
    reliability = sum(
        b.count * (b.mean_forecast - b.observed_frequency) ** 2 for b in curve
    ) / n
    resolution = sum(
        b.count * (b.observed_frequency - base_rate) ** 2 for b in curve
    ) / n
    return SegmentScore(
        segment=name,
        n=n,
        brier=round(brier_score(pairs), 4),
        reliability=round(reliability, 4),
        resolution=round(resolution, 4),
        uncertainty=round(uncertainty, 4),
        base_rate=round(base_rate, 4),
        curve=curve,
    )


def source_class_of(assessment: Assessment) -> str:
    """Dominant source class of the diagnostic evidence, for per-segment
    calibration (A11)."""
    diag = [e for e in assessment.evidence if e.diagnostic_value > 0]
    if not diag:
        return "none"
    if any(not e.source_type.primary for e in diag) and all(
        not e.source_type.primary for e in diag
    ):
        return "relaying"
    if any(not e.source_type.primary for e in diag):
        return "mixed"
    return "primary_objective" if all(e.source_type.objective for e in diag) else "primary_subjective"


def score_pairs(
    labeled: List[Tuple[Pair, str, str]], n_bins: int = 10
) -> ScoreReport:
    """labeled: list of ((forecast, outcome), decision_type, source_class)."""
    overall = score_segment("overall", [p for p, _, _ in labeled], n_bins)
    by_dt: Dict[str, SegmentScore] = {}
    by_sc: Dict[str, SegmentScore] = {}
    for dt in sorted({d for _, d, _ in labeled}):
        by_dt[dt] = score_segment(dt, [p for p, d, _ in labeled if d == dt], n_bins)
    for sc in sorted({s for _, _, s in labeled}):
        by_sc[sc] = score_segment(sc, [p for p, _, s in labeled if s == sc], n_bins)
    return ScoreReport(overall=overall, by_decision_type=by_dt, by_source_class=by_sc)


def score_store(store: CalibrationStore, n_bins: int = 10) -> ScoreReport:
    labeled: List[Tuple[Pair, str, str]] = []
    for s in store.resolved():
        if s.outcome is None:
            continue
        labeled.append(
            ((s.forecast_probability, s.outcome), s.decision_type, s.source_class)
        )
    return score_pairs(labeled, n_bins)
