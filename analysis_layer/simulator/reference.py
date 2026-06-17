"""Mode three: reference cases (PRD Section 7.3).

Curated events with an analyst-graded "good" hypothesis set and matrix. Because
the reasoning nodes are non-deterministic, these are not exact-match assertions;
the harness scores how close the engine's hypothesis set and leading judgment
come to the analyst gold standard, which catches reasoning regressions that
invariants miss.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set

from analysis_layer.config import Settings
from analysis_layer.models.client import ModelClient
from analysis_layer.schema.signals import Scenario
from analysis_layer.simulator.synthetic import run_scenario


@dataclass
class ReferenceCase:
    scenario: Scenario
    gold_hypotheses: Set[str]  # the analyst-graded hypothesis ids
    gold_leading: str


@dataclass
class ReferenceScore:
    case_id: str
    hypothesis_set_overlap: float  # Jaccard against the gold set
    leading_match: bool
    notes: List[str] = field(default_factory=list)

    @property
    def closeness(self) -> float:
        return round(0.5 * self.hypothesis_set_overlap + 0.5 * (1.0 if self.leading_match else 0.0), 4)


def score_reference(
    case: ReferenceCase,
    client: Optional[ModelClient] = None,
    settings: Optional[Settings] = None,
) -> ReferenceScore:
    result = run_scenario(case.scenario, client=client, settings=settings)
    produced = {h.id for h in result.assessment.hypotheses}
    gold = case.gold_hypotheses
    inter = len(produced & gold)
    union = len(produced | gold) or 1
    overlap = round(inter / union, 4)
    leading_match = result.leading_hypothesis == case.gold_leading
    notes = []
    missing = gold - produced
    if missing:
        notes.append(f"missing gold hypotheses: {sorted(missing)}")
    return ReferenceScore(
        case_id=case.scenario.id,
        hypothesis_set_overlap=overlap,
        leading_match=leading_match,
        notes=notes,
    )
