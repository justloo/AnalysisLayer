"""Acceptance gating over the seed library (PRD Sections 7.9, 8, 13).

The frozen suite must clear the Section 7.9 bars on its distribution of runs. The
invariant and fixture gates are enforced in their own modules; here we assert the
behaviour bars and that a per-segment calibration regression would be visible.
"""
from __future__ import annotations

from analysis_layer.simulator.backtest import backtest
from analysis_layer.simulator.loader import load_library
from analysis_layer.simulator.reference import ReferenceCase, score_reference
from analysis_layer.simulator.scoreboard import run_scoreboard


def test_scoreboard_meets_acceptance_bars():
    sb = run_scoreboard(runs=3)
    assert sb.leading_accuracy.mean >= sb.thresholds.leading_accuracy
    assert sb.weak_signal_catch.mean >= sb.thresholds.weak_signal_catch
    assert sb.deception_resistance.mean >= sb.thresholds.deception_resistance
    assert sb.passes()


def test_scoreboard_reports_per_segment_calibration():
    sb = run_scoreboard(runs=2)
    # Calibration must be broken down per segment (A11), not just overall.
    assert sb.calibration.by_source_class
    assert sb.calibration.by_decision_type


def test_backtest_runs_with_anonymization():
    bt = backtest(load_library(), anonymize=True)
    assert bt.anonymized
    assert bt.n_cases >= 1
    assert bt.report.overall.brier == bt.report.overall.brier  # not NaN


def test_reference_case_closeness():
    sc = next(s for s in load_library() if s.id == "price_cut_clean")
    case = ReferenceCase(
        scenario=sc,
        gold_hypotheses={"price_cut", "price_increase", "repackaging", "no_change"},
        gold_leading="price_cut",
    )
    score = score_reference(case)
    assert score.leading_match
    assert score.closeness >= 0.75
