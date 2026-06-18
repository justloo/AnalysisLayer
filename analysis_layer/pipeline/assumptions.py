"""FR-7, Key assumptions check and gap identification (PRD A3.7).

Surface what the leading judgment silently depends on and turn ignorance into
action. Each load-bearing assumption is rated for fragility (how much the
judgment would change if it were wrong). Gaps are emitted as structured
collection requirements, closing the loop back to direction: the layer does not
merely consume signals, it tells collection what to find next.
"""
from __future__ import annotations

from analysis_layer.models import tasks
from analysis_layer.models.client import ModelClient
from analysis_layer.models.tiers import Tier
from analysis_layer.pipeline.weight import collapsed_diagnostic_items, independent_corroboration_for
from analysis_layer.schema.assessment import Assumption
from analysis_layer.schema.state import AnalysisState


def check_assumptions(state: AnalysisState, client: ModelClient) -> AnalysisState:
    leading_id = state.leading_hypothesis_id or "no_change"
    corroboration = independent_corroboration_for(state, leading_id)
    diagnostic_count = sum(1 for e in collapsed_diagnostic_items(state) if e.diagnostic_value > 0)
    res = client.reason(
        tasks.CHECK_ASSUMPTIONS,
        {
            "leading_hypothesis_id": leading_id,
            "independent_corroboration": corroboration,
            "evidence_summaries": [e.content for e in state.evidence],
            "gaps": list(state.gaps),
            "signal_count": len(state.evidence),
            "diagnostic_count": diagnostic_count,
        },
        Tier.strong,
    )
    state.assumptions = [
        Assumption(statement=a["statement"], fragility=float(a["fragility"]))
        for a in res.get("assumptions", [])
    ]
    for gap in res.get("gaps", []):
        if gap not in state.gaps:
            state.gaps.append(gap)
    # F7: thin or non-diagnostic streams must name a coverage gap regardless of verdict.
    _THIN_GAP = (
        "Evidence stream is very thin; seek additional signals before narrowing the assessment."
    )
    # ponytail: single emission site for thin-stream gaps (mock no longer duplicates).
    if diagnostic_count <= 2 and _THIN_GAP not in state.gaps:
        state.gaps.append(_THIN_GAP)
    return state
