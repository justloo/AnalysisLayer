"""FR-4, Hypothesis generation (PRD A3.4, A5).

Produce a hypothesis set as mutually exclusive and exhaustive as the question
allows, BEFORE any evidence is weighed. The set must always include the null
hypothesis, and a deception hypothesis where deception is plausible (R7).

Whether deception is plausible is decided here in code from structural cues (a
reliable, uncorroborated signal pointing at a material move), so the decision is
auditable and not left to model whim. Generation precedes scoring.
"""
from __future__ import annotations

from analysis_layer.models import tasks
from analysis_layer.models.client import ModelClient
from analysis_layer.models.tiers import Tier
from analysis_layer.evidence_bearing import infer_bearing
from analysis_layer.pipeline import scales
from analysis_layer.schema.assessment import Hypothesis, HypothesisStatus
from analysis_layer.schema.state import AnalysisState

_MATERIAL_IDS = {"price_cut", "price_increase", "repackaging"}


def deception_plausible(state: AnalysisState) -> bool:
    """A planted feint is plausible when a reliable source makes an
    uncorroborated claim pointing at a material move (the classic conduit for
    deception, A4.4)."""
    origins_by_claim = {}
    for e in state.evidence:
        claim = infer_bearing(e.content)
        if claim:
            origins_by_claim.setdefault(claim, set()).add(e.origin_id)
    for e in state.evidence:
        claim = infer_bearing(e.content)
        if claim in _MATERIAL_IDS and scales.is_reliable(e.source_reliability):
            if len(origins_by_claim.get(claim, set())) <= 1:
                return True
    return False


def generate_hypotheses(state: AnalysisState, client: ModelClient) -> AnalysisState:
    plausible = deception_plausible(state)
    res = client.reason(
        tasks.GENERATE_HYPOTHESES,
        {
            "decision_type": state.decision_type.value,
            "pir": state.pir_ref,
            "deception_plausible": plausible,
            "evidence_summaries": [e.content for e in state.evidence],
        },
        Tier.strong,
    )
    hyps = [
        Hypothesis(
            id=h["id"],
            statement=h["statement"],
            status=HypothesisStatus.live_alternative,
            is_null=h.get("is_null", False),
            is_deception=h.get("is_deception", False),
        )
        for h in res["hypotheses"]
    ]
    # Safety net: the null hypothesis is always present (R7), regardless of what
    # the model returned.
    if not any(h.is_null for h in hyps):
        hyps.append(
            Hypothesis(
                id="no_change",
                statement="No material pricing change within the window.",
                status=HypothesisStatus.live_alternative,
                is_null=True,
            )
        )
    state.hypotheses = hyps
    return state
