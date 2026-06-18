"""Fix Specification v2.0 Section 6: ensemble, deception positive control, report audit."""
from __future__ import annotations

from pathlib import Path

import pytest

from analysis_layer.config import get_settings
from analysis_layer.pipeline.aggregate import analyze_ensemble
from analysis_layer.schema.assessment import ConfidenceLevel
from analysis_layer.simulator.ensemble_battery import (
    BATTERY_IDS,
    run_ensemble_battery,
    run_ensemble_with_perturbation,
)
from analysis_layer.simulator.loader import load_scenario
from analysis_layer.simulator.report_builder import build_library_reports, build_scenario_report
from analysis_layer.simulator.synthetic import run_scenario

SCENARIOS_DIR = Path(__file__).parent.parent / "analysis_layer" / "simulator" / "scenarios"


def _load(scenario_id: str):
    return load_scenario(SCENARIOS_DIR / f"{scenario_id}.json")


def test_t1_deception_feint_masking_increase_resolves_to_price_increase():
    scenario = _load("deception_feint_masking_increase")
    result = run_scenario(scenario)
    assert result.leading_hypothesis == "price_increase"
    assert result.leading_hypothesis != "price_cut"


def test_section6_true_positive_deception_leads():
    scenario = _load("deception_confirmed_planted_feint")
    result = run_scenario(scenario)
    assert result.leading_hypothesis == "deception"
    assert result.passed
    planted = {
        s.supports
        for s in scenario.signal_stream
        if s.role.value == "deception" and s.supports
    }
    assert result.leading_hypothesis not in planted


@pytest.mark.parametrize("scenario_id", sorted(BATTERY_IDS))
def test_section6_ensemble_matches_single_analyst(scenario_id: str):
    rows = run_ensemble_battery([scenario_id], n_analysts=3)
    row = rows[0]
    assert row.leading_stable
    assert row.posterior_in_bounds


@pytest.mark.parametrize(
    "scenario_id",
    ["high_volume_rich_stream", "only_wrong_data", "only_correct_data"],
)
def test_section6_ensemble_saturation_holds(scenario_id: str):
    scenario = _load(scenario_id)
    ensemble = analyze_ensemble(
        scenario.ordered_signals(), scenario.pir, n_analysts=3, event_id=scenario.id
    )
    p = ensemble.leading_hypothesis().relative_likelihood
    assert p < 0.9999
    assert p <= 0.99


def test_section6_ensemble_disagreement_lowers_confidence():
    base = get_settings()
    scenario = _load("fifty_fifty_mixed")
    unanimous = analyze_ensemble(
        scenario.ordered_signals(),
        scenario.pir,
        n_analysts=3,
        settings_per_analyst=[base, base, base],
        event_id=scenario.id,
    )
    split = run_ensemble_with_perturbation("fifty_fifty_mixed", n_analysts=4)
    assert unanimous.ensemble_disagreement == 0.0
    assert split.ensemble_disagreement >= 0.34
    assert split.confidence.level != ConfidenceLevel.high
    assert split.ensemble_disagreement > unanimous.ensemble_disagreement
    # R18: disagreement must not increase confidence vs the unanimous run.
    rank = {ConfidenceLevel.low: 0, ConfidenceLevel.moderate: 1, ConfidenceLevel.high: 2}
    assert rank[split.confidence.level] <= rank[unanimous.confidence.level]


def test_section6_report_builder_reads_expectations_from_file():
    path = SCENARIOS_DIR / "only_wrong_data.json"
    scenario = _load("only_wrong_data")
    report = build_scenario_report(path)
    assert report.expected_leading_from_file == scenario.expectations.leading_hypothesis
    assert report.result.expected_leading == report.expected_leading_from_file
    assert report.result.leading_hypothesis == report.result.expected_leading


def test_section6_report_builder_all_battery_self_consistent():
    paths = [SCENARIOS_DIR / f"{sid}.json" for sid in sorted(BATTERY_IDS)]
    reports = build_library_reports(paths)
    for report in reports:
        if not report.expected_matches_resolves:
            continue
        assert report.leading_matches_expected or not report.result.released
