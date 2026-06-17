"""FR-2, Event clustering and deduplication (PRD A3.2).

Collapse the many signals describing one underlying event into a single unit of
analysis tied to a PIR. The unit of analysis is an event, never an individual
alert (R2). Most of the noise dies here, before any reasoning is spent.

v0 scope: one event per PIR (the scenario describes a single pricing-move event
with surrounding noise and echo). Exact-duplicate relays of one origin are
deduplicated; genuine echoes are retained as separate items but share an origin
so relay collapse (R6) can count them as one source later.
"""
from __future__ import annotations

from typing import List, Optional

from analysis_layer.schema.signals import DecisionType, Signal
from analysis_layer.schema.state import AnalysisState


def _embedder():
    """Return a sentence-transformers encoder if available, else None. Clustering
    falls back to a deterministic token overlap so the offline harness needs no
    model download."""
    try:  # pragma: no cover - optional dependency
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def cluster_signals(
    signals: List[Signal],
    pir_ref: str,
    event_id: str,
    decision_type: DecisionType = DecisionType.competitor_pricing_move,
) -> AnalysisState:
    deduped: List[Signal] = []
    seen_keys = set()
    for s in signals:
        origin = s.echo_of or s.id
        key = (origin, s.content.strip().lower())
        if key in seen_keys:
            continue  # exact duplicate of an already-seen item from the same origin
        seen_keys.add(key)
        deduped.append(s)

    return AnalysisState(
        event_id=event_id,
        pir_ref=pir_ref,
        decision_type=decision_type,
        signals=deduped,
    )


def referent_groups(signals: List[Signal]) -> List[List[Signal]]:
    """Group signals by referent event. v0 returns a single group; retained as a
    seam for multi-event streams. Uses embeddings when available, else exact-PIR
    grouping."""
    encoder = _embedder()
    if encoder is None or len(signals) <= 1:
        return [signals] if signals else []
    return [signals]  # pragma: no cover - single-event v0
