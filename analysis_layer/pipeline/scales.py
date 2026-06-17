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


def is_reliable(reliability: SourceReliability) -> bool:
    return reliability in _RELIABLE


def is_surprising(credibility: InformationCredibility) -> bool:
    return credibility in _SURPRISING
