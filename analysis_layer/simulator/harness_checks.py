"""Release-blocking harness integrity checks (Fix Spec v2.0 Precondition A)."""
from __future__ import annotations

from analysis_layer.schema.signals import Scenario
from analysis_layer.simulator.synthetic import SyntheticResult


class HarnessIntegrityError(AssertionError):
    """Report or scoreboard field disagrees with authored scenario ground truth."""


def assert_scoreboard_self_consistency(scenario: Scenario, result: SyntheticResult) -> None:
    """T0: displayed expected forecast must match the scenario file, not engine output."""
    authored = scenario.expectations.leading_hypothesis
    if result.expected_leading != authored:
        raise HarnessIntegrityError(
            f"{scenario.id}: result.expected_leading={result.expected_leading!r} "
            f"!= scenario.expectations.leading_hypothesis={authored!r}"
        )
    resolves = scenario.ground_truth.resolves_to
    if authored != resolves:
        # True-positive deception control (Section 6): expectation names the
        # deception hypothesis while ground truth states the material world.
        if authored == "deception" and resolves in {
            "no_change",
            "price_cut",
            "price_increase",
            "repackaging",
        }:
            return
        raise HarnessIntegrityError(
            f"{scenario.id}: expectations.leading_hypothesis={authored!r} "
            f"!= ground_truth.resolves_to={resolves!r}"
        )
