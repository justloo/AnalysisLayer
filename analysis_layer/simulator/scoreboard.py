"""The scoreboard (PRD Section 7.8 and 7.9).

The output of the harness is a curve and a distribution, not a green checkmark.
Across all synthetic judgments it reports leading-hypothesis accuracy, weak-signal
catch rate, deception-resistance rate, and the calibration curve / Brier score
per segment. Because the reasoning nodes are non-deterministic, every benchmark
runs many times and the scoreboard reports the distribution rather than a single
pass. (With the deterministic MockClient the distribution collapses to a point.)
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from analysis_layer.calibration.scoring import ScoreReport, score_pairs, source_class_of
from analysis_layer.config import Settings
from analysis_layer.models.client import ModelClient
from analysis_layer.schema.assessment import RedTeamOutcome
from analysis_layer.schema.signals import Scenario
from analysis_layer.simulator.loader import load_library
from analysis_layer.simulator.synthetic import run_scenario


@dataclass
class BehaviorScore:
    name: str
    values: List[float] = field(default_factory=list)

    @property
    def mean(self) -> float:
        return round(statistics.fmean(self.values), 4) if self.values else float("nan")

    @property
    def lo(self) -> float:
        return round(min(self.values), 4) if self.values else float("nan")

    @property
    def hi(self) -> float:
        return round(max(self.values), 4) if self.values else float("nan")


@dataclass
class AcceptanceThresholds:
    """Section 7.9 bars. Starting proposals, to be set against the base rate of
    the decision type rather than treated as fixed (PRD Section 12)."""

    leading_accuracy: float = 0.8
    weak_signal_catch: float = 1.0
    deception_resistance: float = 1.0
    # Curve distance from the diagonal. A deliberately loose starting bar for the
    # small seed library; tighten it as the resolved set grows (Section 7.9/12).
    max_calibration_reliability: float = 0.2


@dataclass
class Scoreboard:
    n_runs: int
    n_scenarios: int
    leading_accuracy: BehaviorScore
    weak_signal_catch: BehaviorScore
    deception_resistance: BehaviorScore
    confidence_tracking: BehaviorScore
    calibration: ScoreReport
    thresholds: AcceptanceThresholds

    def passes(self) -> bool:
        t = self.thresholds
        ok = self.leading_accuracy.mean >= t.leading_accuracy
        if self.weak_signal_catch.values:
            ok = ok and self.weak_signal_catch.mean >= t.weak_signal_catch
        if self.deception_resistance.values:
            ok = ok and self.deception_resistance.mean >= t.deception_resistance
        rel = self.calibration.overall.reliability
        if rel == rel:  # not NaN
            ok = ok and rel <= t.max_calibration_reliability
        return ok


def run_scoreboard(
    scenarios: Optional[List[Scenario]] = None,
    runs: int = 5,
    client: Optional[ModelClient] = None,
    settings: Optional[Settings] = None,
    thresholds: Optional[AcceptanceThresholds] = None,
) -> Scoreboard:
    scenarios = scenarios or load_library()
    thresholds = thresholds or AcceptanceThresholds()

    leading = BehaviorScore("leading_accuracy")
    weak = BehaviorScore("weak_signal_catch")
    decep = BehaviorScore("deception_resistance")
    conf = BehaviorScore("confidence_tracking")
    labeled = []

    for _ in range(max(1, runs)):
        released_correct = released_total = 0
        weak_caught = weak_total = 0
        decep_resisted = decep_total = 0
        conf_ok = conf_total = 0
        for sc in scenarios:
            r = run_scenario(sc, client=client, settings=settings)
            if r.released:
                released_total += 1
                released_correct += int(r.leading_correct)
                outcome = sc.ground_truth.resolves_to == r.leading_hypothesis
                labeled.append(
                    (
                        (r.assessment.calibration.forecast_probability, outcome),
                        sc.decision_type.value,
                        source_class_of(r.assessment),
                    )
                )
            if r.must_catch_weak_signal:
                weak_total += 1
                weak_caught += int(bool(r.weak_signal_caught))
            if r.must_resist_deception:
                decep_total += 1
                decep_resisted += int(bool(r.deception_resisted))
            conf_total += 1
            conf_ok += int(r.confidence_tracks_quality)

        if released_total:
            leading.values.append(released_correct / released_total)
        if weak_total:
            weak.values.append(weak_caught / weak_total)
        if decep_total:
            decep.values.append(decep_resisted / decep_total)
        if conf_total:
            conf.values.append(conf_ok / conf_total)

    return Scoreboard(
        n_runs=runs,
        n_scenarios=len(scenarios),
        leading_accuracy=leading,
        weak_signal_catch=weak,
        deception_resistance=decep,
        confidence_tracking=conf,
        calibration=score_pairs(labeled),
        thresholds=thresholds,
    )


def render(sb: Scoreboard) -> str:
    lines = []
    lines.append("=" * 64)
    lines.append(f"SCOREBOARD  ({sb.n_scenarios} scenarios x {sb.n_runs} runs)")
    lines.append("=" * 64)

    def fmt(b: BehaviorScore) -> str:
        if not b.values:
            return "n/a"
        return f"{b.mean:.2%}  [{b.lo:.2%} .. {b.hi:.2%}]"

    lines.append(f"Leading-hypothesis accuracy (released): {fmt(sb.leading_accuracy)}")
    lines.append(f"Weak-signal catch rate:                {fmt(sb.weak_signal_catch)}")
    lines.append(f"Deception-resistance rate:             {fmt(sb.deception_resistance)}")
    lines.append(f"Confidence tracks quality:             {fmt(sb.confidence_tracking)}")
    lines.append("-" * 64)
    o = sb.calibration.overall
    lines.append(
        f"Calibration (overall, n={o.n}): Brier={o.brier}  "
        f"reliability={o.reliability} (lower=better)  resolution={o.resolution}"
    )
    for name, seg in sb.calibration.by_source_class.items():
        lines.append(f"  source[{name}] n={seg.n} Brier={seg.brier} reliability={seg.reliability}")
    lines.append("-" * 64)
    lines.append(f"ACCEPTANCE (Section 7.9): {'PASS' if sb.passes() else 'FAIL'}")
    lines.append("=" * 64)
    return "\n".join(lines)
