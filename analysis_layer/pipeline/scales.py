"""Numeric scales for the Admiralty grading axes.

These convert the qualitative reliability/credibility grades (A4.1) into the
weights the diagnosticity and confidence arithmetic consume. They are code, not
model judgment: the model judges the grade, the code computes with it.
"""
from __future__ import annotations

from analysis_layer.schema.assessment import InformationCredibility, SourceReliability

# Reliability (about the source). 'F' (cannot be judged) is mid-low, not zero:
# absence of a track record is uncertainty, not unreliability (A4.1).
RELIABILITY_WEIGHT = {
    SourceReliability.A: 1.0,
    SourceReliability.B: 0.85,
    SourceReliability.C: 0.6,
    SourceReliability.D: 0.35,
    SourceReliability.E: 0.15,
    SourceReliability.F: 0.45,
}

# Credibility (about the item). '6' (cannot be judged) is mid-low for the same
# reason.
CREDIBILITY_WEIGHT = {
    InformationCredibility.one: 1.0,
    InformationCredibility.two: 0.85,
    InformationCredibility.three: 0.65,
    InformationCredibility.four: 0.4,
    InformationCredibility.five: 0.2,
    InformationCredibility.six: 0.45,
}

_SURPRISING = {InformationCredibility.four, InformationCredibility.five}
_RELIABLE = {SourceReliability.A, SourceReliability.B}


def grade_weight(reliability: SourceReliability, credibility: InformationCredibility) -> float:
    """Combined evidentiary weight in [0, 1]. The two axes are kept independent
    (R4) and blended evenly so neither alone dominates."""
    return 0.5 * RELIABILITY_WEIGHT[reliability] + 0.5 * CREDIBILITY_WEIGHT[credibility]


def reliability_weight(reliability: SourceReliability) -> float:
    """Source-reliability axis only (F6 weak-signal scoring)."""
    return RELIABILITY_WEIGHT[reliability]


# Items below this combined grade weight are "low quality" for F1/F3 weak-unanimity
# collapse and the uniform-low-grade red-team check.
QUALITY_FLOOR = 0.55


def scoring_weight(
    reliability: SourceReliability,
    credibility: InformationCredibility,
    *,
    weak_signal: bool = False,
) -> float:
    """Weight used in net diagnosticity arithmetic (F1, F6).

    Weak signals use reliability only, decoupled from corroboration-suppressed
    credibility (R5, F6)."""
    if weak_signal:
        return reliability_weight(reliability)
    return grade_weight(reliability, credibility)


def is_low_grade(reliability: SourceReliability, credibility: InformationCredibility) -> bool:
    return grade_weight(reliability, credibility) < QUALITY_FLOOR


def is_high_grade(reliability: SourceReliability, credibility: InformationCredibility) -> bool:
    """A or B reliability with credibility 1 or 2."""
    return reliability in {SourceReliability.A, SourceReliability.B} and credibility in {
        InformationCredibility.one,
        InformationCredibility.two,
    }


def is_reliable(reliability: SourceReliability) -> bool:
    return reliability in _RELIABLE


def is_surprising(credibility: InformationCredibility) -> bool:
    return credibility in _SURPRISING
