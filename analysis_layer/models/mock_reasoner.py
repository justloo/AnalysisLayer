"""Deterministic handlers backing the MockClient.

This is a test double, not the product's intelligence. It lets the full pipeline
and the entire simulator run offline with zero API keys (PRD Section 9.2), so the
code nodes, invariants, and scenario plumbing are exercisable the moment they
exist. A real provider (GoogleAIClient) replaces it without any pipeline change.

Design rule honored here: the mock forms cell judgments and grades from
*observable* signal framing (the `supports` hint, source type, reliability,
echo_of), never from a scenario's hidden ground truth or a signal's `role`. That
keeps deception-resistance and weak-signal-catch honest tests rather than the
engine being handed the answer.
"""
from __future__ import annotations

from typing import Dict, List

from analysis_layer.models import tasks

# The v0 hypothesis template for competitor pricing moves (PRD Section 3).
_PRICING_TEMPLATE = [
    {"id": "price_cut", "statement": "The competitor will cut prices on a tracked product line.",
     "is_null": False, "is_deception": False},
    {"id": "price_increase", "statement": "The competitor will raise prices on a tracked product line.",
     "is_null": False, "is_deception": False},
    {"id": "repackaging", "statement": "The competitor will repackage or restructure tiers without a headline price change.",
     "is_null": False, "is_deception": False},
    {"id": "no_change", "statement": "No material pricing change within the window.",
     "is_null": True, "is_deception": False},
]
_DECEPTION = {
    "id": "deception",
    "statement": "A visible pricing signal is a planted feint intended to mislead.",
    "is_null": False,
    "is_deception": True,
}
_MATERIAL_IDS = {"price_cut", "price_increase", "repackaging"}


def _generate_hypotheses(payload: dict) -> dict:
    """Return the refined hypothesis set. Always includes the null (R7); includes
    the deception hypothesis only when the caller judged deception plausible
    from structural cues (FR-4: appears when the scenario warrants it)."""
    hyps: List[dict] = [dict(h) for h in _PRICING_TEMPLATE]
    if payload.get("deception_plausible"):
        hyps.append(dict(_DECEPTION))
    return {"hypotheses": hyps}


def _judge_cell(payload: dict) -> dict:
    """Consistency of one evidence item vs one hypothesis (A3.5).

    Rules (from observable framing only):
      - non-diagnostic noise (supports is None) is consistent with everything;
      - an item pointing at hypothesis X is consistent with X, inconsistent with
        other material hypotheses, and inconsistent with the null;
      - the deception hypothesis is consistent with any material-pointing item
        (a feint can mimic a real move), so material indicators never accrue as
        evidence *against* deception. Deception is held down by its low base rate
        and surfaced by the red team, not by the matrix.
    """
    supports = payload.get("supports")
    hyp = payload["hypothesis"]
    hid = hyp["id"]
    is_null = hyp.get("is_null", False)
    is_deception = hyp.get("is_deception", False)

    if supports is None:
        return {"judgment": "consistent", "rationale": "Non-diagnostic: consistent with all hypotheses."}
    if is_deception:
        return {"judgment": "consistent", "rationale": "A material signal could be a planted feint."}
    if is_null:
        return {"judgment": "inconsistent", "rationale": "A material indicator is inconsistent with no change."}
    if supports == hid:
        return {"judgment": "consistent", "rationale": "Item points to this hypothesis."}
    if supports in _MATERIAL_IDS:
        return {"judgment": "inconsistent", "rationale": "Item points to a different material outcome."}
    return {"judgment": "not_applicable", "rationale": "No clear bearing."}


def _grade_evidence(payload: dict) -> dict:
    """Infer reliability/credibility when not hand-fed (M2). Reliability comes
    from source structure; credibility from corroboration and plausibility, kept
    independent of reliability (R4). A reliable but uncorroborated surprising
    claim keeps high reliability and low credibility (an off-diagonal grade)
    rather than collapsing onto the diagonal."""
    primary = payload.get("primary", True)
    objective = payload.get("objective", True)
    corroborated = payload.get("corroborated", False)
    surprising = payload.get("surprising", False)

    if objective and primary:
        reliability = "B"
    elif primary:
        reliability = "C"
    elif objective:
        reliability = "C"
    else:
        reliability = "D"

    if corroborated:
        credibility = "2"
    elif surprising:
        credibility = "4"  # doubtful on its face, but NOT downgraded into silence
    else:
        credibility = "3"

    return {
        "source_reliability": reliability,
        "information_credibility": credibility,
        "rationale": (
            f"Reliability from source structure (primary={primary}, objective={objective}); "
            f"credibility from corroboration={corroborated}, surprising={surprising}, scored independently."
        ),
    }


def _classify_source_type(payload: dict) -> dict:
    content = (payload.get("content") or "").lower()
    relaying_cues = ["reports that", "according to", "as reported", "cites", "per ", "wire"]
    subjective_cues = ["believes", "thinks", "rumor", "specul", "expects", "claims"]
    is_relaying = payload.get("echo_of") is not None or any(c in content for c in relaying_cues)
    is_subjective = any(c in content for c in subjective_cues)
    return {"primary": not is_relaying, "objective": not is_subjective}


def _check_assumptions(payload: dict) -> dict:
    leading = payload.get("leading_hypothesis_id", "no_change")
    corroboration = payload.get("independent_corroboration", 1)
    assumptions = [
        {
            "statement": "Observed signals reflect genuine intent rather than an A/B test or staging artifact.",
            "fragility": 0.5 if leading in _MATERIAL_IDS else 0.3,
        },
        {
            "statement": "The tracked product line is representative of the competitor's broader pricing posture.",
            "fragility": 0.35,
        },
    ]
    gaps: List[str] = []
    if corroboration <= 1 and leading in _MATERIAL_IDS:
        gaps.append("Seek a second independent source confirming the leading pricing move.")
    return {"assumptions": assumptions, "gaps": gaps}


def _red_team(payload: dict) -> dict:
    """Narrative challenges atop the structural checks the node computes in code.

    The mock raises a challenge when the structural cues the node passes in are
    present. The hard, blocking decisions (single-source recompute, deception
    cap) are made by code in redteam.py, not here."""
    challenges: List[str] = []
    if payload.get("single_source_dependent"):
        challenges.append(
            "Single-source dependency: the leading judgment collapses if the top origin is removed."
        )
    if payload.get("deception_cue"):
        challenges.append(
            "Deception: a reliable but uncorroborated signal conveniently points to a dramatic move; "
            "it may be planted."
        )
    if payload.get("mirror_imaging_cue"):
        challenges.append(
            "Mirror-imaging: the inference assumes the competitor reasons as the operator would."
        )
    if payload.get("thin_margin"):
        challenges.append(
            "Single-hypothesis fixation risk: the leading hypothesis barely beat the next alternative."
        )
    return {"challenges_raised": challenges}


def _synthesize(payload: dict) -> dict:
    leading_statement = payload.get("leading_statement", "No material change is expected.")
    likelihood_phrase = payload.get("likelihood_phrase", "roughly even chance")
    leading_id = payload.get("leading_hypothesis_id", "no_change")

    bluf = f"{leading_statement} Assessed as {likelihood_phrase} within the 30-day window."
    key_judgments = [leading_statement]
    if payload.get("top_gap"):
        key_judgments.append(f"Key gap: {payload['top_gap']}")
    if leading_id in _MATERIAL_IDS:
        action = (
            "Decision input: factor a possible competitor pricing move into the upcoming pricing "
            "decision and pre-stage a response; do not yet commit."
        )
    else:
        action = (
            "Decision input: no pre-emptive pricing action indicated; continue monitoring the watch list."
        )
    return {"bluf": bluf, "key_judgments": key_judgments, "recommended_action": action}


_HANDLERS = {
    tasks.GENERATE_HYPOTHESES: _generate_hypotheses,
    tasks.JUDGE_CELL: _judge_cell,
    tasks.GRADE_EVIDENCE: _grade_evidence,
    tasks.CLASSIFY_SOURCE_TYPE: _classify_source_type,
    tasks.CHECK_ASSUMPTIONS: _check_assumptions,
    tasks.RED_TEAM: _red_team,
    tasks.SYNTHESIZE: _synthesize,
}


def handle(task: str, payload: Dict) -> Dict:
    handler = _HANDLERS.get(task)
    if handler is None:
        raise KeyError(f"MockClient has no handler for task '{task}'")
    return handler(payload)
