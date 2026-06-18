"""Ensemble battery runner (Fix Spec Section 6, R18).

Runs the mechanism + volume battery through multi-analyst aggregation to verify
suppression, saturation, and disagreement handling do not regress under ensemble.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace
from pathlib import Path
from typing import List, Optional

from analysis_layer.config import Settings, get_settings
from analysis_layer.pipeline.aggregate import analyze_ensemble
from analysis_layer.schema.assessment import Assessment
from analysis_layer.simulator.loader import load_scenario
from analysis_layer.simulator.synthetic import run_scenario

BATTERY_IDS = (
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
    "deception_confirmed_planted_feint",
)

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


@dataclass
class EnsembleBatteryRow:
    scenario_id: str
    expected_leading: str
    single_analyst_leading: str
    ensemble_leading: str
    ensemble_disagreement: float
    leading_posterior: float
    notes: List[str] = field(default_factory=list)

    @property
    def leading_stable(self) -> bool:
        return self.ensemble_leading == self.single_analyst_leading

    @property
    def posterior_in_bounds(self) -> bool:
        return 0.01 <= self.leading_posterior <= 0.99


def skeptical_settings(base: Optional[Settings] = None) -> Settings:
    """Perturbed priors for disagreement injection in ensemble tests."""
    base = base or get_settings()
    rates = dict(base.base_rates)
    rates.update({"no_change": 0.72, "price_cut": 0.06, "price_increase": 0.08, "deception": 0.06})
    return replace(base, base_rates=rates, update_k=0.8)


def materialist_settings(base: Optional[Settings] = None) -> Settings:
    base = base or get_settings()
    rates = dict(base.base_rates)
    rates.update({"no_change": 0.12, "price_cut": 0.42, "price_increase": 0.28, "deception": 0.03})
    return replace(base, base_rates=rates, update_k=4.5)


def run_ensemble_battery(
    scenario_ids: Optional[List[str]] = None,
    n_analysts: int = 3,
) -> List[EnsembleBatteryRow]:
    ids = scenario_ids or list(BATTERY_IDS)
    rows: List[EnsembleBatteryRow] = []
    for sid in ids:
        scenario = load_scenario(SCENARIOS_DIR / f"{sid}.json")
        single = run_scenario(scenario)
        ensemble = analyze_ensemble(
            scenario.ordered_signals(),
            scenario.pir,
            n_analysts=n_analysts,
            event_id=scenario.id,
        )
        leading = ensemble.leading_hypothesis()
        rows.append(
            EnsembleBatteryRow(
                scenario_id=sid,
                expected_leading=scenario.expectations.leading_hypothesis,
                single_analyst_leading=single.leading_hypothesis,
                ensemble_leading=leading.id if leading else "no_change",
                ensemble_disagreement=ensemble.ensemble_disagreement,
                leading_posterior=leading.relative_likelihood if leading else 0.0,
            )
        )
    return rows


def run_ensemble_with_perturbation(scenario_id: str, n_analysts: int = 4) -> Assessment:
    scenario = load_scenario(SCENARIOS_DIR / f"{scenario_id}.json")
    base = get_settings()
    skeptical = skeptical_settings(base)
    materialist = materialist_settings(base)
    settings_list = [skeptical, materialist] * (max(1, n_analysts) // 2 + 1)
    return analyze_ensemble(
        scenario.ordered_signals(),
        scenario.pir,
        n_analysts=n_analysts,
        settings_per_analyst=settings_list[:n_analysts],
        event_id=scenario.id,
    )
