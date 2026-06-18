"""Deterministic handlers backing the MockClient.

This is a test double, not the product's intelligence. Cell judgments are formed
from evidence *content* only (Precondition B); the `supports` field on signals is
harness ground-truth metadata and is never passed into the matrix judge.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from analysis_layer.models import tasks
from analysis_layer.evidence_bearing import (
    describes_deception_operation,
    feint_target_bearing,
    infer_bearing,
    is_forward_looking,
)

_PRICING_TEMPLATE = [
    {
        "id": "price_cut",
        "statement": "The competitor will cut prices on a tracked product line.",
        "is_null": False,
        "is_deception": False,
    },
    {
        "id": "price_increase",
        "statement": "The competitor will raise prices on a tracked product line.",
        "is_null": False,
        "is_deception": False,
    },
    {
        "id": "repackaging",
        "statement": "The competitor will repackage or restructure tiers without a headline price change.",
        "is_null": False,
        "is_deception": False,
    },
    {
        "id": "no_change",
        "statement": "No material pricing change within the window.",
        "is_null": True,
        "is_deception": False,
    },
]
# F2: falsifiable deception claim — a feint masking a *different* move can be
# disconfirmed by corroborated evidence for the visible move.
_DECEPTION = {
    "id": "deception",
    "statement": (
        "Visible pricing signals are a planted feint masking a different imminent "
        "move (not the move they appear to show)."
    ),
    "is_null": False,
    "is_deception": True,
}
_MATERIAL_IDS = {"price_cut", "price_increase", "repackaging"}


def _generate_hypotheses(payload: dict) -> dict:
    hyps: List[dict] = [dict(h) for h in _PRICING_TEMPLATE]
    if payload.get("deception_plausible"):
        hyps.append(dict(_DECEPTION))
    return {"hypotheses": hyps}


def _judge_cell(payload: dict) -> dict:
    """Consistency judged from content only (Precondition B, F4)."""
    content = payload.get("evidence", {}).get("content", "")
    hyp = payload["hypothesis"]
    hid = hyp["id"]
    is_null = hyp.get("is_null", False)
    is_deception = hyp.get("is_deception", False)
    bearing = infer_bearing(content)

    # F2: deception is scored when content explicitly names a planted operation.
    if is_deception:
        if describes_deception_operation(content):
            return {
                "judgment": "consistent",
                "rationale": "Content confirms an active deception or planted feint.",
            }
        return {
            "judgment": "not_applicable",
            "rationale": "Deception is a meta-hypothesis; not scored without explicit cues.",
        }

    if describes_deception_operation(content):
        if is_null:
            return {
                "judgment": "consistent",
                "rationale": "Planted-feint intelligence is consistent with no genuine move.",
            }
        target = feint_target_bearing(content)
        if target and hid == target:
            return {
                "judgment": "inconsistent",
                "rationale": "Intelligence names this visible move as a planted feint.",
            }
        if hid in _MATERIAL_IDS:
            return {
                "judgment": "not_applicable",
                "rationale": "Deception intelligence does not directly bear on this alternative.",
            }
        return {
            "judgment": "not_applicable",
            "rationale": "Deception intelligence does not directly bear on this alternative.",
        }

    if bearing is None:
        return {"judgment": "consistent", "rationale": "Non-diagnostic: consistent with all hypotheses."}

    # F4: forward-looking hiring/packaging signals do not strongly rule out a
    # near-term price move on a different track.
    if is_forward_looking(content) and hid in _MATERIAL_IDS and bearing != hid:
        return {
            "judgment": "not_applicable",
            "rationale": "Forward-looking signal; weak bearing on a near-term pricing move.",
        }

    if bearing == hid:
        return {"judgment": "consistent", "rationale": "Content supports this hypothesis."}
    if is_null:
        return {"judgment": "inconsistent", "rationale": "A material indicator is inconsistent with no change."}
    if bearing in _MATERIAL_IDS:
        return {"judgment": "inconsistent", "rationale": "Content points to a different material outcome."}
    return {"judgment": "not_applicable", "rationale": "No clear bearing."}


def _grade_evidence(payload: dict) -> dict:
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
        credibility = "4"
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
    # Thin-stream gaps are emitted in assumptions.check_assumptions (F7).
    return {"assumptions": assumptions, "gaps": gaps}


def _red_team(payload: dict) -> dict:
    challenges: List[str] = []
    if payload.get("single_source_dependent"):
        challenges.append(
            "Single-source dependency: the leading judgment collapses if the top origin is removed."
        )
    if payload.get("uniform_low_grade_dependency"):
        challenges.append(
            "Uniform low-grade dependency: every diagnostic item supporting the leading "
            "hypothesis is below the quality floor with no primary objective corroboration."
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
