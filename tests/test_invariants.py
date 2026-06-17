"""Mode two: invariants (PRD Section 7.2).

Pass-or-fail gates that must hold on every run. These map to R5, R6, R7, R13,
R16 and block any change if they fail.
"""
from __future__ import annotations

import pytest

from analysis_layer.simulator.invariants import run_all_invariants
from analysis_layer.simulator.synthetic import run_scenario

pytestmark = pytest.mark.invariants


def test_all_invariants_pass_on_seed_library(library):
    failures = []
    for scenario in library:
        result = run_scenario(scenario)
        for inv in run_all_invariants(scenario, result.assessment):
            if not inv.passed:
                failures.append(f"{scenario.id}: {inv.name} - {inv.detail}")
    assert not failures, "invariant failures:\n" + "\n".join(failures)


def test_null_hypothesis_always_present(library):
    for scenario in library:
        result = run_scenario(scenario)
        assert any(h.is_null for h in result.assessment.hypotheses), scenario.id


def test_red_team_blocks_deception_trap(library):
    trap = next(s for s in library if s.id == "deception_trap")
    result = run_scenario(trap)
    # The red team must fire on a planted trap, and the deception is resisted.
    assert result.assessment.red_team.outcome.value != "passed"
    assert result.deception_resisted is True


def test_weak_signal_is_escalated_not_buried(library):
    ws = next(s for s in library if s.id == "weak_signal")
    result = run_scenario(ws)
    assert result.weak_signal_caught is True
    weak_ev = [e for e in result.assessment.evidence if e.weak_signal]
    assert weak_ev, "weak signal was buried"
    assert result.assessment.gaps or result.assessment.indicators_watch
