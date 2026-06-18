"""FR-5, Evidence-by-hypothesis matrix and diagnosticity (PRD A3.5).

Build the ACH matrix as explicit, inspectable state (R19): hypotheses across the
top, evidence down the side, each cell judged consistent / inconsistent / not
applicable by the model. Then score each item's diagnosticity in code: an item
consistent with every hypothesis discriminates nothing and is near-worthless
regardless of how vivid it is (R8); an item that splits the hypotheses carries
the weight.

This is the stage where the machine's lack of a working-memory limit matters
most: it holds the whole grid a human cannot.
"""
from __future__ import annotations

from analysis_layer.models import tasks
from analysis_layer.models.client import ModelClient
from analysis_layer.models.tiers import Tier
from analysis_layer.schema.state import AnalysisState, MatrixCell, MatrixJudgment


def build_matrix(state: AnalysisState, client: ModelClient) -> AnalysisState:
    cells = []
    for e in state.evidence:
        for h in state.hypotheses:
            # Precondition B: judge from content only; never pass `supports` (harness
            # ground truth) into the consistency judgment call.
            res = client.reason(
                tasks.JUDGE_CELL,
                {
                    "evidence": {"id": e.id, "content": e.content},
                    "hypothesis": {
                        "id": h.id,
                        "statement": h.statement,
                        "is_null": h.is_null,
                        "is_deception": h.is_deception,
                    },
                },
                Tier.fast,
            )
            cells.append(
                MatrixCell(
                    evidence_id=e.id,
                    hypothesis_id=h.id,
                    judgment=MatrixJudgment(res["judgment"]),
                    rationale=res.get("rationale", ""),
                )
            )
    state.matrix = cells
    score_diagnosticity(state)
    return state


def score_diagnosticity(state: AnalysisState) -> None:
    """Diagnostic value in [0, 1] = how much an item discriminates across the
    live hypotheses.

    Diagnosticity follows Heuer's disconfirmation emphasis: an item's analytic
    value is how many hypotheses it rules out. An item consistent with every
    hypothesis rules out none and is near-worthless regardless of how vivid it is
    (R8); an item consistent with one hypothesis and inconsistent with the rest
    is highly diagnostic. So the score is the fraction of applicable hypotheses
    the item is inconsistent with."""
    for e in state.evidence:
        judgments = [
            c.judgment
            for c in state.matrix
            if c.evidence_id == e.id and c.judgment != MatrixJudgment.not_applicable
        ]
        if not judgments:
            e.diagnostic_value = 0.0
            continue
        inconsistent = sum(1 for j in judgments if j == MatrixJudgment.inconsistent)
        e.diagnostic_value = round(inconsistent / len(judgments), 4)
