"""FR-1, Intake and source typing (PRD A3.1).

Turn a raw signal into a normalized signal with full provenance and a structural
source-type tag. Classifying the source's type at intake is load-bearing: the
corrected evaluation model (A4) depends on it everywhere downstream.

Failure mode guarded against: treating a relay as a source. The structural type
(primary vs relaying) is captured here so echo can be collapsed later (R6).
"""
from __future__ import annotations

from datetime import timezone
from typing import List

from analysis_layer.models import tasks
from analysis_layer.models.client import ModelClient
from analysis_layer.models.tiers import Tier
from analysis_layer.schema.signals import EpistemicType, ProvenanceType, Signal


def run_intake(signals: List[Signal], client: ModelClient) -> List[Signal]:
    normalized: List[Signal] = []
    for s in signals:
        s2 = s.model_copy(deep=True)
        if s2.provenance_type is None or s2.epistemic_type is None:
            res = client.reason(
                tasks.CLASSIFY_SOURCE_TYPE,
                {"content": s2.content, "echo_of": s2.echo_of},
                Tier.fast,
            )
            if s2.provenance_type is None:
                s2.provenance_type = (
                    ProvenanceType.primary if res.get("primary", True) else ProvenanceType.relaying
                )
            if s2.epistemic_type is None:
                s2.epistemic_type = (
                    EpistemicType.objective if res.get("objective", True) else EpistemicType.subjective
                )
        # A relay, by definition, is not primary even if not otherwise marked.
        if s2.echo_of is not None:
            s2.provenance_type = ProvenanceType.relaying
        if s2.timestamp is not None and s2.timestamp.tzinfo is None:
            s2.timestamp = s2.timestamp.replace(tzinfo=timezone.utc)
        normalized.append(s2)
    return normalized
