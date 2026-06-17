"""Calibration scoring and store tests (PRD A11, FR-13)."""
from __future__ import annotations

from analysis_layer.calibration.scoring import (
    brier_score,
    calibration_curve,
    score_pairs,
    source_class_of,
)
from analysis_layer.calibration.store import MemoryStore, StoredAssessment
from analysis_layer.schema.assessment import CalibrationStatus
from analysis_layer.simulator.synthetic import run_scenario


def test_brier_perfect_forecasts_is_zero():
    assert brier_score([(1.0, True), (0.0, False)]) == 0.0


def test_brier_worst_forecasts_is_one():
    assert brier_score([(0.0, True), (1.0, False)]) == 1.0


def test_calibration_curve_bins_outcomes():
    pairs = [(0.9, True), (0.9, True), (0.1, False), (0.1, False)]
    curve = calibration_curve(pairs, n_bins=10)
    # Two populated bins, each perfectly observed.
    high = next(b for b in curve if b.lower == 0.9)
    low = next(b for b in curve if b.lower == 0.1)
    assert high.observed_frequency == 1.0
    assert low.observed_frequency == 0.0


def test_store_resolve_records_outcome_and_brier(library):
    store = MemoryStore()
    a = run_scenario(library[0]).assessment
    store.save(
        StoredAssessment(
            assessment=a,
            decision_type="competitor_pricing_move",
            source_class=source_class_of(a),
            forecast_probability=a.calibration.forecast_probability,
        )
    )
    store.resolve(a.id, outcome=True, brier_contribution=0.04)
    resolved = store.get(a.id)
    assert resolved.status == CalibrationStatus.proved_out
    assert resolved.brier_contribution == 0.04
    assert len(store.resolved()) == 1


def test_score_pairs_segments_by_label():
    labeled = [
        ((0.8, True), "competitor_pricing_move", "primary_objective"),
        ((0.3, False), "competitor_pricing_move", "relaying"),
    ]
    report = score_pairs(labeled)
    assert report.overall.n == 2
    assert "primary_objective" in report.by_source_class
    assert "relaying" in report.by_source_class
