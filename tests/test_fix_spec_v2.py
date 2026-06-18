"""Fix Specification v2.0 regression suite (Section 4)."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from analysis_layer.schema.assessment import ConfidenceLevel
from analysis_layer.schema.signals import Scenario
from analysis_layer.simulator.harness_checks import assert_scoreboard_self_consistency
from analysis_layer.simulator.loader import load_library, load_scenario
from analysis_layer.simulator.synthetic import run_scenario

SCENARIOS_DIR = Path(__file__).parent.parent / "analysis_layer" / "simulator" / "scenarios"

BATTERY_IDS = {
    "price_cut_flow_baseline",
    "deception_feint_masking_increase",
    "weak_signal_early_cut",
    "echo_inflation_no_real_signal",
    "mirror_imaging_trap",
    "noise_pileup_vs_signal",
    "thin_evidence_honest_null",
    "high_volume_rich_stream",
    "minimal_single_signal",
    "only_correct_data",
    "only_wrong_data",
    "fifty_fifty_mixed",
}

FROZEN_CORRECT = {
    "echo_inflation_no_real_signal",
    "noise_pileup_vs_signal",
    "mirror_imaging_trap",
    "minimal_single_signal",
    "fifty_fifty_mixed",
}

SATURATION_ANCHORS = {
    "high_volume_rich_stream",
    "only_correct_data",
    "mirror_imaging_trap",
    "noise_pileup_vs_signal",
}


def _load(scenario_id: str) -> Scenario:
    return load_scenario(SCENARIOS_DIR / f"{scenario_id}.json")


@pytest.mark.parametrize("scenario_id", sorted(BATTERY_IDS))
def test_t0_scoreboard_self_consistency(scenario_id: str):
    scenario = _load(scenario_id)
    result = run_scenario(scenario)
    assert_scoreboard_self_consistency(scenario, result)


def _scramble_supports(scenario: Scenario) -> Scenario:
    sc = copy.deepcopy(scenario)
    flip = {
        "price_cut": "price_increase",
        "price_increase": "repackaging",
        "repackaging": "price_cut",
        "no_change": "price_cut",
    }
    for sig in sc.signal_stream:
        if sig.supports:
            sig.supports = flip.get(sig.supports, sig.supports)
    return sc


@pytest.mark.parametrize("scenario_id", ["price_cut_flow_baseline", "only_wrong_data"])
def test_t_label_supports_scramble_does_not_change_leading(scenario_id: str):
    scenario = _load(scenario_id)
    baseline = run_scenario(scenario)
    scrambled = run_scenario(_scramble_supports(scenario))
    assert scrambled.leading_hypothesis == baseline.leading_hypothesis


def test_t1_catch_all_cannot_win_price_cut_flow_baseline():
    scenario = _load("price_cut_flow_baseline")
    result = run_scenario(scenario)
    assert result.leading_hypothesis == "price_cut"
    assert result.leading_hypothesis != "deception"


def test_t1_deception_feint_masking_increase():
    scenario = _load("deception_feint_masking_increase")
    result = run_scenario(scenario)
    assert result.leading_hypothesis == "price_increase"


def test_t2_weak_signal_early_cut_resolves_to_price_cut():
    scenario = _load("weak_signal_early_cut")
    result = run_scenario(scenario)
    assert result.leading_hypothesis == "price_cut"


def test_t3_thin_evidence_honest_null():
    scenario = _load("thin_evidence_honest_null")
    result = run_scenario(scenario)
    assert result.leading_hypothesis == "no_change"
    assert result.assessment.confidence.level == ConfidenceLevel.low
    assert len(result.assessment.gaps) >= 1


def test_t4_only_wrong_data():
    scenario = _load("only_wrong_data")
    result = run_scenario(scenario)
    leading = result.leading_hypothesis
    assert leading == "no_change"
    assert result.assessment.confidence.level == ConfidenceLevel.low
    challenges = " ".join(result.assessment.red_team.challenges_raised).lower()
    assert "uniform low-grade" in challenges or "low-grade dependency" in challenges


@pytest.mark.parametrize("scenario_id", sorted(SATURATION_ANCHORS))
def test_t_sat_posterior_within_lexicon_bounds(scenario_id: str):
    scenario = _load(scenario_id)
    result = run_scenario(scenario)
    p = result.assessment.leading_hypothesis().relative_likelihood
    assert 0.01 <= p <= 0.99
    assert p < 0.9999


@pytest.mark.parametrize("scenario_id", sorted(FROZEN_CORRECT))
def test_t5_frozen_directional_verdicts(scenario_id: str):
    scenario = _load(scenario_id)
    result = run_scenario(scenario)
    assert result.leading_hypothesis == scenario.expectations.leading_hypothesis


def test_t0_all_library_scenarios_self_consistent():
    for scenario in load_library():
        result = run_scenario(scenario)
        if scenario.expectations.leading_hypothesis != scenario.ground_truth.resolves_to:
            pytest.skip(f"{scenario.id}: expectations and resolves_to intentionally differ")
        assert_scoreboard_self_consistency(scenario, result)
