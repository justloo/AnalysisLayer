"""Mode two: invariants (PRD Section 7.2).

Properties that must hold on every run regardless of content, run as assertions
against live pipeline output. These are pass-or-fail gates mapping to R5, R6, R7,
R13, and R16:

  - the null hypothesis is always present (R7);
  - a high-reliability uncorroborated surprising claim is always escalated,
    never buried (R5);
  - echo never counts as corroboration (R6);
  - likelihood and confidence never share a sentence (R13);
  - the red team can actually block (R16), verified by trap scenarios.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from analysis_layer.schema.assessment import Assessment, LikelihoodTerm, RedTeamOutcome
from analysis_layer.schema.signals import Scenario, SignalRole


@dataclass
class InvariantResult:
    name: str
    passed: bool
    detail: str = ""


_CONFIDENCE_WORDS = ["high confidence", "moderate confidence", "low confidence"]
_LIKELIHOOD_TERMS = [t.value for t in LikelihoodTerm]


def check_null_present(assessment: Assessment) -> InvariantResult:
    ok = any(h.is_null for h in assessment.hypotheses)
    return InvariantResult("null_hypothesis_present", ok, "" if ok else "no null hypothesis in set")


def check_likelihood_confidence_separation(assessment: Assessment) -> InvariantResult:
    """No single sentence may contain both a likelihood term and a confidence
    level (R13). The schema already keeps them in separate fields; this guards
    the generated prose (BLUF, key judgments)."""
    texts = [assessment.bluf, *assessment.key_judgments, assessment.recommended_action]
    for text in texts:
        for sentence in re.split(r"(?<=[.!?])\s+", text or ""):
            low = sentence.lower()
            has_like = any(term in low for term in _LIKELIHOOD_TERMS)
            has_conf = any(word in low for word in _CONFIDENCE_WORDS)
            if has_like and has_conf:
                return InvariantResult(
                    "likelihood_confidence_separation",
                    False,
                    f"sentence mixes likelihood and confidence: {sentence!r}",
                )
    return InvariantResult("likelihood_confidence_separation", True)


def check_echo_not_corroboration(scenario: Scenario, assessment: Assessment) -> InvariantResult:
    """Distinct origins must collapse echo: the count of independent origins is
    strictly less than the count of evidence items when echoes are present (R6).
    """
    has_echo = any(s.role == SignalRole.echo or s.echo_of for s in scenario.signal_stream)
    if not has_echo:
        return InvariantResult("echo_not_corroboration", True, "no echo in scenario")
    n_items = len(assessment.evidence)
    n_origins = len({e.origin_id for e in assessment.evidence})
    ok = n_origins < n_items
    return InvariantResult(
        "echo_not_corroboration",
        ok,
        f"origins={n_origins} items={n_items}" if not ok else "",
    )


def check_weak_signal_escalated(scenario: Scenario, assessment: Assessment) -> InvariantResult:
    weak_ids = {s.id for s in scenario.signal_stream if s.role == SignalRole.weak_signal}
    if not weak_ids:
        return InvariantResult("weak_signal_escalated", True, "no weak signal in scenario")
    for wid in weak_ids:
        ev = next((e for e in assessment.evidence if e.id == wid), None)
        if ev is None or not ev.weak_signal:
            return InvariantResult(
                "weak_signal_escalated", False, f"weak signal {wid} buried (not flagged)"
            )
    return InvariantResult("weak_signal_escalated", bool(assessment.gaps or assessment.indicators_watch))


def check_red_team_can_block(scenario: Scenario, assessment: Assessment) -> InvariantResult:
    """For trap scenarios (deception or single-source), the red team must fire or
    the engine must not take the planted bait (R16)."""
    is_trap = any(
        s.role in (SignalRole.deception,) for s in scenario.signal_stream
    ) or scenario.expectations.must_resist_deception
    if not is_trap:
        return InvariantResult("red_team_can_block", True, "not a trap scenario")

    leading = assessment.leading_hypothesis().id if assessment.leading_hypothesis() else None
    planted_targets = {
        s.supports for s in scenario.signal_stream if s.role == SignalRole.deception and s.supports
    }
    if leading == "deception":
        return InvariantResult("red_team_can_block", True, "deception correctly identified")
    if planted_targets and leading and leading not in planted_targets:
        return InvariantResult("red_team_can_block", True, "planted bait not taken")

    ok = assessment.red_team.outcome != RedTeamOutcome.passed
    return InvariantResult(
        "red_team_can_block",
        ok,
        "" if ok else "red team passed a planted trap (rubber stamp)",
    )


def run_universal_invariants(assessment: Assessment) -> List[InvariantResult]:
    """Invariants that must hold for any assessment, content-independent."""
    return [
        check_null_present(assessment),
        check_likelihood_confidence_separation(assessment),
    ]


def run_all_invariants(scenario: Scenario, assessment: Assessment) -> List[InvariantResult]:
    results = run_universal_invariants(assessment)
    results.append(check_echo_not_corroboration(scenario, assessment))
    results.append(check_weak_signal_escalated(scenario, assessment))
    results.append(check_red_team_can_block(scenario, assessment))
    return results
