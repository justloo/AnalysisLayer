"""Mode five: backtesting on history (PRD Section 7.5).

Real resolved events, replayed with only the information that existed before the
outcome resolved, scored for calibration. This is the Good Judgment Project
method used as a test. Its failure mode is lookahead leakage, where the model
already knows how the story ended. The defenses are mandatory:

  - prefer events after the model's training cutoff;
  - anonymize/transform entities so a case is not recognizable;
  - lean on synthetic scenarios for probing specific behaviors.

Here a "historical" case is a resolved scenario; the harness applies the
anonymization transform before replay and scores Brier/calibration on the
resolved outcomes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from analysis_layer.calibration.scoring import ScoreReport, score_pairs, source_class_of
from analysis_layer.config import Settings
from analysis_layer.models.client import ModelClient
from analysis_layer.schema.signals import Scenario
from analysis_layer.simulator.synthetic import run_scenario

# Entity tokens to neutralize so a replayed case is not recognizable (defense
# against lookahead leakage via memorized specifics).
_ENTITY_PATTERNS = [
    (re.compile(r"\$\d[\d,]*"), "$XX"),
    (re.compile(r"\b(Austin|TechWire|StartupDaily)\b"), "REGION"),
]


@dataclass
class BacktestResult:
    n_cases: int
    report: ScoreReport
    anonymized: bool


def anonymize_scenario(scenario: Scenario) -> Scenario:
    """Return a copy with surface entity specifics neutralized. Crucially it does
    NOT touch the ground truth or the structural framing, only recognizable
    surface tokens."""
    clone = scenario.model_copy(deep=True)
    for sig in clone.signal_stream:
        text = sig.content
        for pat, repl in _ENTITY_PATTERNS:
            text = pat.sub(repl, text)
        sig.content = text
    return clone


def backtest(
    history: List[Scenario],
    anonymize: bool = True,
    client: Optional[ModelClient] = None,
    settings: Optional[Settings] = None,
) -> BacktestResult:
    labeled = []
    for case in history:
        replay = anonymize_scenario(case) if anonymize else case
        result = run_scenario(replay, client=client, settings=settings)
        if not result.released:
            continue  # a returned-for-collection event is not a forecast
        outcome = case.ground_truth.resolves_to == result.leading_hypothesis
        labeled.append(
            (
                (result.assessment.calibration.forecast_probability, outcome),
                case.decision_type.value,
                source_class_of(result.assessment),
            )
        )
    return BacktestResult(
        n_cases=len(labeled), report=score_pairs(labeled), anonymized=anonymize
    )
