"""Schema contract tests (PRD Section 6 / A10)."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from analysis_layer.schema.assessment import (
    Assessment,
    Band,
    Hypothesis,
    HypothesisStatus,
)
from analysis_layer.simulator.synthetic import run_scenario


def test_band_rejects_inverted_interval():
    with pytest.raises(ValidationError):
        Band(low=0.8, high=0.2)


def test_assessment_requires_exactly_one_leading(library):
    sc = library[0]
    a = run_scenario(sc).assessment
    leading = [h for h in a.hypotheses if h.status == HypothesisStatus.leading]
    assert len(leading) == 1


def test_assessment_roundtrips_through_json(library):
    a = run_scenario(library[0]).assessment
    restored = Assessment.model_validate_json(a.model_dump_json())
    assert restored.id == a.id
    assert restored.leading_hypothesis().id == a.leading_hypothesis().id


def test_likelihood_and_confidence_are_separate_fields(library):
    a = run_scenario(library[0]).assessment
    # Distinct typed fields; neither leaks into the other (R13).
    assert a.likelihood.term is not None
    assert a.confidence.level is not None
    assert not hasattr(a.likelihood, "level")
