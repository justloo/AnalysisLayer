"""FR-8, Adversarial review (PRD A3.8, A9).

A dedicated red-team pass attacks the leading judgment before it ships. It runs
the fixed bias catalog and, critically, has genuine authority: a successful
challenge downgrades confidence or returns the event for collection (R16). A
red team that can only annotate is theater.

The structural checks are computed in code (single-source recompute, deception
cues, thin margin) because they are arithmetic; the model contributes the
narrative challenges on top. Both can trigger blocking.
"""
from __future__ import annotations

from typing import Dict, Optional

from analysis_layer.config import Settings, get_settings
from analysis_layer.models import tasks
from analysis_layer.models.client import ModelClient
from analysis_layer.models.tiers import Tier
from analysis_layer.pipeline import scales
from analysis_layer.pipeline.test_step import hypothesis_margin
from analysis_layer.pipeline.weight import independent_corroboration_for
from analysis_layer.schema.assessment import RedTeam, RedTeamOutcome
from analysis_layer.schema.state import AnalysisState, MatrixJudgment

_MATERIAL_IDS = {"price_cut", "price_increase", "repackaging"}
_THIN_MARGIN = 0.15

_BIAS_CATALOG = [
    "confirmation",
    "anchoring",
    "mirror_imaging",
    "vividness_availability",
    "single_source_dependency",
    "single_hypothesis_fixation",
    "deception",
]


def run_red_team(
    state: AnalysisState, client: ModelClient, settings: Optional[Settings] = None
) -> AnalysisState:
    settings = settings or get_settings()
    leading_id = state.leading_hypothesis_id
    challenges = []
    flags: Dict[str, bool] = {}

    # --- single-source dependency (A9): does the conclusion collapse if the top
    # origin is removed? "Collapse" means no independent origin still corroborates
    # the leading material judgment. A weaker-but-present second source is NOT a
    # single-source dependency. -----------------------------------------------
    top_origin = _top_supporting_origin(state, leading_id)
    single_source_dependent = False
    collapses = False
    if top_origin is not None and leading_id in _MATERIAL_IDS:
        if _corroboration_excluding(state, leading_id, top_origin) == 0:
            single_source_dependent = True
            collapses = True
    flags["single_source_dependency"] = single_source_dependent

    # --- deception cue --------------------------------------------------------
    deception_present = any(h.is_deception for h in state.hypotheses)
    deception_cue = (
        deception_present
        and leading_id in _MATERIAL_IDS
        and independent_corroboration_for(state, leading_id) <= 1
        and _leading_driver_is_uncorroborated_reliable(state, leading_id)
    )
    flags["deception"] = deception_cue

    # --- single-hypothesis fixation / thin margin -----------------------------
    margin = hypothesis_margin(state)
    thin_margin = margin < _THIN_MARGIN
    flags["single_hypothesis_fixation"] = thin_margin

    # --- mirror-imaging (subjective-only inference of a material move) ---------
    mirror_imaging = leading_id in _MATERIAL_IDS and _leading_support_all_subjective(state, leading_id)
    flags["mirror_imaging"] = mirror_imaging

    # Narrative challenges from the model, given the structural cues.
    res = client.reason(
        tasks.RED_TEAM,
        {
            "leading_hypothesis_id": leading_id,
            "single_source_dependent": single_source_dependent,
            "deception_cue": deception_cue,
            "mirror_imaging_cue": mirror_imaging,
            "thin_margin": thin_margin,
        },
        Tier.strong,
    )
    challenges.extend(res.get("challenges_raised", []))

    # --- decide the outcome (the part with teeth, R16) ------------------------
    outcome = RedTeamOutcome.passed
    if collapses or (deception_cue and independent_corroboration_for(state, leading_id) <= 1):
        outcome = RedTeamOutcome.returned_for_collection
        state.returned_for_collection = True
        state.confidence_cap_low = True
        if collapses and "Single-source dependency" not in " ".join(challenges):
            challenges.append(
                "Single-source dependency: the leading judgment collapses without one origin; "
                "returned for corroborating collection."
            )
        if deception_cue:
            challenges.append(
                "Deception not ruled out on a single-sourced material move; returned for collection."
            )
    elif single_source_dependent or thin_margin or mirror_imaging:
        outcome = RedTeamOutcome.confidence_downgraded
        state.confidence_cap_low = True

    state.red_team = RedTeam(
        checks_run=list(_BIAS_CATALOG),
        challenges_raised=challenges,
        outcome=outcome,
    )
    state.red_team_flags = flags
    return state


# --- helpers -----------------------------------------------------------------


def _top_supporting_origin(state: AnalysisState, leading_id: Optional[str]) -> Optional[str]:
    if leading_id is None:
        return None
    contribution: Dict[str, float] = {}
    for cell in state.matrix:
        if cell.hypothesis_id != leading_id or cell.judgment != MatrixJudgment.consistent:
            continue
        e = state.evidence_by_id(cell.evidence_id)
        if e is None or e.diagnostic_value <= 0:
            continue
        w = e.diagnostic_value * scales.grade_weight(e.source_reliability, e.information_credibility)
        contribution[e.origin_id] = contribution.get(e.origin_id, 0.0) + w
    if not contribution:
        return None
    return max(contribution, key=contribution.get)


def _corroboration_excluding(state: AnalysisState, hypothesis_id: Optional[str], origin_id: str) -> int:
    if hypothesis_id is None:
        return 0
    origins = set()
    for cell in state.matrix:
        if cell.hypothesis_id != hypothesis_id or cell.judgment != MatrixJudgment.consistent:
            continue
        e = state.evidence_by_id(cell.evidence_id)
        if e is None or e.diagnostic_value <= 0 or e.origin_id == origin_id:
            continue
        origins.add(e.origin_id)
    return len(origins)


def _leading_driver_is_uncorroborated_reliable(state: AnalysisState, leading_id: str) -> bool:
    for cell in state.matrix:
        if cell.hypothesis_id != leading_id or cell.judgment != MatrixJudgment.consistent:
            continue
        e = state.evidence_by_id(cell.evidence_id)
        if e is None or e.diagnostic_value <= 0:
            continue
        if scales.is_reliable(e.source_reliability) and scales.is_surprising(
            e.information_credibility
        ):
            return True
    return False


def _leading_support_all_subjective(state: AnalysisState, leading_id: str) -> bool:
    supporters = [
        state.evidence_by_id(c.evidence_id)
        for c in state.matrix
        if c.hypothesis_id == leading_id and c.judgment == MatrixJudgment.consistent
    ]
    supporters = [e for e in supporters if e is not None and e.diagnostic_value > 0]
    if not supporters:
        return False
    return all(not e.source_type.objective for e in supporters)
