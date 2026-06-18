"""FR-3, Relay collapse and weak-signal handling (PRD A4.2 defects 2 and 3).

Two corrections to naive Admiralty grading live here:

  - Relay collapse (R6): relays are collapsed to their origin so echo across many
    outlets of one wire story counts as one source, not many. Corroboration is
    counted over distinct origins, never raw item count.

  - Weak-signal protection (R5): a high-reliability source making an
    uncorroborated, surprising claim is treated as a live weak signal. It is NOT
    downgraded into silence; it is escalated as a gap and routed to the watch
    list and collection. Lack of corroboration becomes a reason to look harder.
"""
from __future__ import annotations

from typing import Dict, Set

from analysis_layer.pipeline import scales
from analysis_layer.evidence_bearing import infer_bearing
from analysis_layer.schema.assessment import IndicatorDirection, IndicatorWatch
from analysis_layer.schema.state import AnalysisState


def weight_event(state: AnalysisState) -> AnalysisState:
    # Map each claim (the hypothesis a signal points to) to the set of distinct
    # origins asserting it, so corroboration is counted independent of echo.
    origins_by_claim: Dict[str, Set[str]] = {}
    for e in state.evidence:
        claim = infer_bearing(e.content)
        if claim is None:
            continue
        origins_by_claim.setdefault(claim, set()).add(e.origin_id)

    for e in state.evidence:
        claim = infer_bearing(e.content)
        independent_origins = len(origins_by_claim.get(claim, set())) if claim else 0
        uncorroborated = claim is not None and independent_origins <= 1
        if (
            scales.is_reliable(e.source_reliability)
            and scales.is_surprising(e.information_credibility)
            and uncorroborated
        ):
            e.weak_signal = True
            gap = (
                f"Weak signal from a reliable source is uncorroborated: '{_short(e.content)}'. "
                "Seek independent corroboration before discounting."
            )
            if gap not in state.gaps:
                state.gaps.append(gap)
            state.indicators_watch.append(
                IndicatorWatch(
                    indicator=f"Independent corroboration of: {_short(e.content)}",
                    direction=IndicatorDirection.confirms,
                    resolution_criterion=(
                        "A second, independent (non-relaying) source reports the same move "
                        "within the window."
                    ),
                )
            )
    return state


def collapsed_diagnostic_items(state: AnalysisState):
    """One representative diagnostic item per origin (R6): the highest-graded
    diagnostic item from each origin. Used so echo volume does not inflate the
    aggregate evidence grade."""
    best = {}
    for e in state.evidence:
        if e.diagnostic_value <= 0:
            continue
        cur = best.get(e.origin_id)
        if cur is None or scales.grade_weight(
            e.source_reliability, e.information_credibility
        ) > scales.grade_weight(cur.source_reliability, cur.information_credibility):
            best[e.origin_id] = e
    return list(best.values())


def independent_corroboration_for(state: AnalysisState, hypothesis_id: str) -> int:
    """Distinct origins whose evidence is consistent with the hypothesis and is
    diagnostic. Echo across relays of one origin counts once (R6)."""
    origins: Set[str] = set()
    for cell in state.matrix:
        if cell.hypothesis_id != hypothesis_id or cell.judgment.value != "consistent":
            continue
        e = state.evidence_by_id(cell.evidence_id)
        if e is not None and e.diagnostic_value > 0:
            origins.add(e.origin_id)
    return len(origins)


def _short(text: str, n: int = 60) -> str:
    return text if len(text) <= n else text[: n - 1] + "\u2026"
