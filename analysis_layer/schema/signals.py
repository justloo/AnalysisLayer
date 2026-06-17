"""Input contract: raw signals and the declarative scenario format.

A signal carries provenance and the PIR it was collected against (PRD A0 input
contract). The scenario format is the authored ground-truth declaration the
synthetic simulator injects (PRD Section 7.4).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from analysis_layer.schema.assessment import (
    InformationCredibility,
    SourceReliability,
)


class DecisionType(str, Enum):
    competitor_pricing_move = "competitor_pricing_move"


class ProvenanceType(str, Enum):
    primary = "primary"
    relaying = "relaying"


class EpistemicType(str, Enum):
    subjective = "subjective"
    objective = "objective"


class SignalRole(str, Enum):
    """Authoring-time label of a signal's role in a scenario. Used by the harness
    to score behaviour (e.g. must_catch_weak_signal). The pipeline does NOT read
    role to form judgments, so deception-resistance and weak-signal-catch remain
    honest tests rather than the engine being told the answer."""

    genuine_indicator = "genuine_indicator"
    noise = "noise"
    echo = "echo"
    weak_signal = "weak_signal"
    deception = "deception"


class Signal(BaseModel):
    """A raw incoming signal. In M1 grading hints may be supplied directly
    (graded inputs hand-fed); from M2 the front end infers grades from content.
    """

    id: str
    content: str
    pir_ref: str
    timestamp: Optional[datetime] = None

    # Provenance (PRD A0/A3.1).
    url_or_handle: Optional[str] = None
    capture_method: Optional[str] = None

    # Structural typing. May be supplied or inferred at intake (A3.1).
    provenance_type: Optional[ProvenanceType] = None
    epistemic_type: Optional[EpistemicType] = None
    echo_of: Optional[str] = None  # origin id this relays, or None

    # Grading hints. In a scenario these are authored truth; intake/grade uses
    # them as priors in M1 and as scoring truth in the harness.
    declared_source_reliability: Optional[SourceReliability] = None
    declared_information_credibility: Optional[InformationCredibility] = None

    # Which hypothesis id the content points to (observable framing the mock
    # reasoner uses to build matrix cells). A real model infers this from
    # content; harness ground-truth scoring never depends on it.
    supports: Optional[str] = None

    # Authoring metadata (scenario scoring only; not used to form judgments).
    role: Optional[SignalRole] = None
    true_source_reliability: Optional[SourceReliability] = None


class ScenarioGroundTruth(BaseModel):
    state: str  # the true world state, hidden from the pipeline
    resolves_to: str  # the outcome the forecast is scored against (a hypothesis id)


class ScenarioExpectations(BaseModel):
    leading_hypothesis: str  # expected leading hypothesis id
    must_catch_weak_signal: bool = False
    must_resist_deception: bool = False
    confidence_tracks: str = "evidence_quality_not_volume"


class Scenario(BaseModel):
    """The declarative scenario the operator authors (PRD Section 7.4)."""

    id: str
    decision_type: DecisionType = DecisionType.competitor_pricing_move
    pir: str
    ground_truth: ScenarioGroundTruth
    signal_stream: List[Signal] = Field(default_factory=list)
    expectations: ScenarioExpectations

    def ordered_signals(self) -> List[Signal]:
        """Signals in timestamp order, as collection would deliver them."""
        return sorted(
            self.signal_stream,
            key=lambda s: (s.timestamp is None, s.timestamp or datetime.min),
        )
