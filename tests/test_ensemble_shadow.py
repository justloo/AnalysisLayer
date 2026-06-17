"""M6 tests: ensemble aggregation (FR-12, R18) and shadow mode (Section 7.6)."""
from __future__ import annotations

from analysis_layer.calibration.store import MemoryStore
from analysis_layer.pipeline.aggregate import analyze_ensemble
from analysis_layer.simulator.shadow import shadow_run


def test_ensemble_runs_and_preserves_disagreement_field(library):
    sc = next(s for s in library if s.id == "price_cut_clean")
    a = analyze_ensemble(sc.ordered_signals(), sc.pir, n_analysts=3, event_id=sc.id)
    assert a.leading_hypothesis().id == "price_cut"
    # Deterministic backend => analysts agree => disagreement is 0, but the field
    # is always present and surfaced (R18).
    assert a.ensemble_disagreement == 0.0


def test_shadow_logs_without_acting(library):
    store = MemoryStore()
    baselines = {"price_cut_clean": "price_cut", "deception_trap": "price_cut"}
    obs = shadow_run(library, store=store, baselines=baselines)
    assert len(obs) == len(library)
    assert len(store.all()) == len(library)
    # The deception trap baseline (a human fooled into 'price_cut') disagrees with
    # the layer, which is exactly the kind of signal shadow mode surfaces.
    trap = next(o for o in obs if o.assessment_id == "deception_trap")
    assert trap.agrees_with_baseline is False
