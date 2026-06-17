"""FR-3, Source and information grading (PRD A3.3, A4).

Grade the quality of what is known before reasoning on it, using the corrected
two-axis model: source reliability (about the source) and information
credibility (about the item), scored INDEPENDENTLY so off-diagonal grades are
possible (R4). A high-reliability source making a surprising claim must be able
to receive, e.g., an A4 (reliable source, currently doubtful item) rather than
collapsing onto the diagonal.

In M1 grades are hand-fed (graded inputs); from M2 they are inferred by the model
when not supplied. Every grade carries its rationale (R19).
"""
from __future__ import annotations

from analysis_layer.models import tasks
from analysis_layer.models.client import ModelClient
from analysis_layer.models.tiers import Tier
from analysis_layer.schema.assessment import (
    Evidence,
    InformationCredibility,
    Provenance,
    SourceReliability,
    SourceType,
)
from analysis_layer.schema.signals import ProvenanceType
from analysis_layer.schema.state import AnalysisState


def grade_event(state: AnalysisState, client: ModelClient) -> AnalysisState:
    evidence = []
    for s in state.signals:
        primary = s.provenance_type != ProvenanceType.relaying
        objective = (s.epistemic_type is None) or (s.epistemic_type.value == "objective")
        origin_id = s.echo_of or s.id

        if s.declared_source_reliability is not None and s.declared_information_credibility is not None:
            reliability = s.declared_source_reliability
            credibility = s.declared_information_credibility
            rationale = "Hand-fed grade (graded input, M1)."
        else:
            corroborated = _has_independent_corroboration(state, s)
            surprising = s.declared_information_credibility in (
                InformationCredibility.four,
                InformationCredibility.five,
            )
            res = client.reason(
                tasks.GRADE_EVIDENCE,
                {
                    "content": s.content,
                    "primary": primary,
                    "objective": objective,
                    "corroborated": corroborated,
                    "surprising": surprising,
                },
                Tier.fast,
            )
            reliability = SourceReliability(res["source_reliability"])
            credibility = InformationCredibility(res["information_credibility"])
            rationale = res.get("rationale", "")

        evidence.append(
            Evidence(
                id=s.id,
                content=s.content,
                source_reliability=reliability,
                information_credibility=credibility,
                source_type=SourceType(primary=primary, objective=objective),
                origin_id=origin_id,
                provenance=Provenance(
                    url_or_handle=s.url_or_handle,
                    captured_at=s.timestamp,
                    capture_method=s.capture_method,
                ),
                grade_rationale=rationale,
            )
        )
    state.evidence = evidence
    return state


def _has_independent_corroboration(state: AnalysisState, signal) -> bool:
    """True if another signal from a different origin makes the same claim."""
    if signal.supports is None:
        return False
    origin = signal.echo_of or signal.id
    for other in state.signals:
        if other.id == signal.id:
            continue
        other_origin = other.echo_of or other.id
        if other_origin != origin and other.supports == signal.supports:
            return True
    return False
