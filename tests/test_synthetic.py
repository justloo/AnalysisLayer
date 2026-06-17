"""Mode four: synthetic scenario simulation (PRD Section 7.4)."""
from __future__ import annotations

import pytest

from analysis_layer.simulator.synthetic import run_scenario

pytestmark = pytest.mark.synthetic


def test_every_seed_scenario_passes(library):
    failures = []
    for scenario in library:
        result = run_scenario(scenario)
        if not result.passed:
            failures.append(f"{scenario.id}: leading={result.leading_hypothesis} notes={result.notes}")
    assert not failures, "scenario failures:\n" + "\n".join(failures)


def test_clean_price_cut_is_released_and_correct(library):
    sc = next(s for s in library if s.id == "price_cut_clean")
    r = run_scenario(sc)
    assert r.released
    assert r.leading_hypothesis == "price_cut"
    assert r.assessment.likelihood.term.value in {"likely", "very likely", "almost certain"}


def test_run_to_run_stability_with_mock(library):
    # The deterministic backend must produce identical leading hypothesis and
    # confidence across repeated runs (Section 7.9 run-to-run stability).
    sc = next(s for s in library if s.id == "price_cut_clean")
    first = run_scenario(sc)
    for _ in range(3):
        again = run_scenario(sc)
        assert again.leading_hypothesis == first.leading_hypothesis
        assert again.assessment.confidence.level == first.assessment.confidence.level
        assert again.assessment.calibration.forecast_probability == first.assessment.calibration.forecast_probability
