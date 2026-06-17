"""Pipeline state: the explicit, inspectable working object the orchestrator
threads through every stage.

The evidence-by-hypothesis matrix is held here as explicit state rather than
implied inside a prompt (PRD Section 9.1, R19), which is what lets the system
reason over more hypotheses than a human can and makes the reasoning auditable.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from analysis_layer.schema.assessment import (
    Assumption,
    Confidence,
    Evidence,
    Hypothesis,
    IndicatorWatch,
    Likelihood,
    RedTeam,
)
from analysis_layer.schema.signals import DecisionType, Signal


class MatrixJudgment(str, Enum):
    """Per-cell consistency of one evidence item against one hypothesis (A3.5)."""

    consistent = "consistent"
    inconsistent = "inconsistent"
    not_applicable = "not_applicable"


class MatrixCell(BaseModel):
    evidence_id: str
    hypothesis_id: str
    judgment: MatrixJudgment
    rationale: str = ""


class AnalysisState(BaseModel):
    """Mutable working state for a single event under analysis.

    One AnalysisState corresponds to one event tied to a PIR (R2), never a raw
    alert. The orchestrator populates fields stage by stage.
    """

    event_id: str
    pir_ref: str
    decision_type: DecisionType = DecisionType.competitor_pricing_move

    signals: List[Signal] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)

    # The evidence-by-hypothesis matrix, keyed (evidence_id, hypothesis_id).
    matrix: List[MatrixCell] = Field(default_factory=list)

    # Posterior over hypotheses after disconfirmation/updating (A6). Keyed by id.
    posteriors: Dict[str, float] = Field(default_factory=dict)
    # Diagnostic evidence weight against each hypothesis (R9). Keyed by id.
    evidence_against: Dict[str, float] = Field(default_factory=dict)
    leading_hypothesis_id: Optional[str] = None

    assumptions: List[Assumption] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    indicators_watch: List[IndicatorWatch] = Field(default_factory=list)

    red_team: RedTeam = Field(default_factory=RedTeam)
    # Red-team authority signals consumed by the confidence node (R16): a
    # successful challenge can cap confidence low or return the event.
    confidence_cap_low: bool = False
    red_team_flags: Dict[str, bool] = Field(default_factory=dict)
    confidence: Optional[Confidence] = None
    likelihood: Optional[Likelihood] = None

    bluf: str = ""
    key_judgments: List[str] = Field(default_factory=list)
    recommended_action: str = ""

    # Bookkeeping for the orchestrator's enforced stage order (R3).
    stages_completed: List[str] = Field(default_factory=list)
    returned_for_collection: bool = False

    # --- helpers -------------------------------------------------------------

    def cell(self, evidence_id: str, hypothesis_id: str) -> Optional[MatrixCell]:
        for c in self.matrix:
            if c.evidence_id == evidence_id and c.hypothesis_id == hypothesis_id:
                return c
        return None

    def hypothesis(self, hypothesis_id: str) -> Optional[Hypothesis]:
        for h in self.hypotheses:
            if h.id == hypothesis_id:
                return h
        return None

    def evidence_by_id(self, evidence_id: str) -> Optional[Evidence]:
        for e in self.evidence:
            if e.id == evidence_id:
                return e
        return None

    def null_hypothesis(self) -> Optional[Hypothesis]:
        for h in self.hypotheses:
            if h.is_null:
                return h
        return None

    def independent_origin_count(self) -> int:
        """Distinct origins after relay collapse (R6): echo is not corroboration."""
        return len({e.origin_id for e in self.evidence})
