"""The assessment object: the structured product the layer emits.

This is the contract every consumer and the simulator build against. It is the
canonical schema from PRD Section 6 / Appendix A10, expressed as pydantic v2
models so FR-11 ("validates against the schema") is enforced by construction.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Band(BaseModel):
    """A numeric probability/score interval, rendered as [low, high]."""

    low: float = Field(ge=0.0, le=1.0)
    high: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _ordered(self) -> "Band":
        if self.high < self.low:
            raise ValueError("Band.high must be >= Band.low")
        return self

    def contains(self, p: float) -> bool:
        return self.low <= p <= self.high

    def __str__(self) -> str:  # e.g. "55-80%"
        return f"{round(self.low * 100)}-{round(self.high * 100)}%"


# --- Likelihood: ICD 203 lexicon (PRD A7) ------------------------------------


class LikelihoodTerm(str, Enum):
    almost_no_chance = "almost no chance"
    very_unlikely = "very unlikely"
    unlikely = "unlikely"
    roughly_even_chance = "roughly even chance"
    likely = "likely"
    very_likely = "very likely"
    almost_certain = "almost certain"


class Likelihood(BaseModel):
    """Probability of the event/judgment. A separate quantity from confidence
    (R13): likelihood and confidence never share a field or sentence. The
    numeric band is always rendered beside the term (R14)."""

    term: LikelihoodTerm
    probability_band: Band

    def rendered(self) -> str:
        return f"{self.term.value} ({self.probability_band})"


# --- Confidence: computed five-factor model (PRD A8) -------------------------


class ConfidenceLevel(str, Enum):
    high = "high"
    moderate = "moderate"
    low = "low"


class ConfidenceDrivers(BaseModel):
    """The five auditable factors confidence is computed from (A8, R15).

    Each is scored 0..1 (higher is stronger support for the judgment)."""

    evidence_grade: float = Field(ge=0.0, le=1.0)
    independent_corroboration: float = Field(ge=0.0, le=1.0)
    hypothesis_margin: float = Field(ge=0.0, le=1.0)
    assumption_fragility: float = Field(ge=0.0, le=1.0)
    question_coverage: float = Field(ge=0.0, le=1.0)


class Confidence(BaseModel):
    level: ConfidenceLevel
    band: Band
    drivers: ConfidenceDrivers


# --- Evidence and grading (PRD A4) -------------------------------------------


class SourceReliability(str, Enum):
    """Admiralty source-reliability axis (about the source). 'F' means there is
    no basis to judge, not that the source is untrustworthy (A4.1)."""

    A = "A"  # completely reliable
    B = "B"  # usually reliable
    C = "C"  # fairly reliable
    D = "D"  # not usually reliable
    E = "E"  # unreliable
    F = "F"  # reliability cannot be judged


class InformationCredibility(str, Enum):
    """Admiralty information-credibility axis (about the item)."""

    one = "1"  # confirmed by other independent sources
    two = "2"  # probably true
    three = "3"  # possibly true
    four = "4"  # doubtful
    five = "5"  # improbable
    six = "6"  # credibility cannot be judged


class Provenance(BaseModel):
    url_or_handle: Optional[str] = None
    captured_at: Optional[datetime] = None
    capture_method: Optional[str] = None


class SourceType(BaseModel):
    """Structural type captured at intake (A3.1), used everywhere downstream.

    Rendered as "primary | relaying ; subjective | objective" per the schema."""

    primary: bool = True  # primary (first-hand) vs relaying (echoing another)
    objective: bool = True  # objective (sensor/filing/price page) vs subjective

    def rendered(self) -> str:
        return (
            f"{'primary' if self.primary else 'relaying'} ; "
            f"{'objective' if self.objective else 'subjective'}"
        )


class Evidence(BaseModel):
    id: str
    content: str
    source_reliability: SourceReliability
    information_credibility: InformationCredibility
    source_type: SourceType
    origin_id: str  # relays collapse to a shared origin (R6)
    provenance: Provenance = Field(default_factory=Provenance)
    diagnostic_value: float = Field(ge=0.0, le=1.0, default=0.0)
    grade_rationale: str = ""
    # Weak-signal protection (R5): a high-reliability uncorroborated surprising
    # claim is escalated rather than buried. Tracked here so synthesis/red team
    # and the simulator can verify it was not silently downgraded.
    weak_signal: bool = False


# --- Hypotheses (PRD A5) -----------------------------------------------------


class HypothesisStatus(str, Enum):
    leading = "leading"
    rejected = "rejected"
    live_alternative = "live-alternative"


class Hypothesis(BaseModel):
    id: str
    statement: str
    status: HypothesisStatus = HypothesisStatus.live_alternative
    rationale: str = ""
    relative_likelihood: float = Field(ge=0.0, le=1.0, default=0.0)
    is_null: bool = False  # the mundane / no-change hypothesis (R7)
    is_deception: bool = False  # the planted/feint hypothesis (R7)


# --- Assumptions, gaps, watch list (PRD A3.7, A3.11) -------------------------


class Assumption(BaseModel):
    statement: str
    fragility: float = Field(ge=0.0, le=1.0)  # how much the judgment moves if wrong


class IndicatorDirection(str, Enum):
    confirms = "confirms"
    breaks = "breaks"


class IndicatorWatch(BaseModel):
    indicator: str
    direction: IndicatorDirection
    resolution_criterion: str  # what counts as resolved, for scoring (R17)


# --- Adversarial review (PRD A9) ---------------------------------------------


class RedTeamOutcome(str, Enum):
    passed = "passed"
    confidence_downgraded = "confidence-downgraded"
    returned_for_collection = "returned-for-collection"


class RedTeam(BaseModel):
    checks_run: List[str] = Field(default_factory=list)
    challenges_raised: List[str] = Field(default_factory=list)
    outcome: RedTeamOutcome = RedTeamOutcome.passed


# --- Calibration (PRD A11) ---------------------------------------------------


class CalibrationStatus(str, Enum):
    open = "open"
    proved_out = "proved_out"
    disproved = "disproved"


class Calibration(BaseModel):
    resolvable_claim: str
    status: CalibrationStatus = CalibrationStatus.open
    brier_contribution: Optional[float] = None
    # The probability the leading judgment proves out, stored for Brier scoring.
    forecast_probability: float = Field(ge=0.0, le=1.0, default=0.5)


# --- The assessment object (PRD Section 6 / A10) -----------------------------


class Assessment(BaseModel):
    id: str
    pir_ref: str
    created_at: datetime = Field(default_factory=_utcnow)
    bluf: str

    likelihood: Likelihood
    confidence: Confidence

    key_judgments: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    assumptions: List[Assumption] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    indicators_watch: List[IndicatorWatch] = Field(default_factory=list)
    recommended_action: str = ""

    red_team: RedTeam = Field(default_factory=RedTeam)
    human_overrides: List[str] = Field(default_factory=list)
    calibration: Calibration

    # Ensemble disagreement preserved as a confidence signal (R18); 0 when a
    # single analyst ran. Surfaced rather than averaged away.
    ensemble_disagreement: float = Field(ge=0.0, le=1.0, default=0.0)

    @model_validator(mode="after")
    def _exactly_one_leading(self) -> "Assessment":
        leading = [h for h in self.hypotheses if h.status == HypothesisStatus.leading]
        if self.hypotheses and len(leading) != 1:
            raise ValueError("assessment must have exactly one leading hypothesis")
        return self

    def leading_hypothesis(self) -> Optional[Hypothesis]:
        for h in self.hypotheses:
            if h.status == HypothesisStatus.leading:
                return h
        return None
