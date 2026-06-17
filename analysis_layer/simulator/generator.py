"""The scenario-generator agent (PRD Section 7.7).

An adversarial agent whose job is to invent synthetic scenarios designed to break
the pipeline: the same critique-loop instinct the layer runs internally, turned
on the whole system. Candidate scenarios are reviewed and the useful ones are
added to the frozen library; this keeps the test set adversarial and growing
rather than static.

The deterministic implementation here mutates known traps (echo amplification,
single-source deception, buried weak signal) into fresh variants. With a real
provider the GENERATE_SCENARIO task lets the model invent novel ones; either way
candidates are returned for human review, never auto-frozen.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from analysis_layer.models.client import ModelClient
from analysis_layer.schema.assessment import InformationCredibility, SourceReliability
from analysis_layer.schema.signals import (
    DecisionType,
    EpistemicType,
    ProvenanceType,
    Scenario,
    ScenarioExpectations,
    ScenarioGroundTruth,
    Signal,
    SignalRole,
)

_T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
_PIR = "Will the tracked competitor make a material pricing change within 30 days?"


def _sig(i, content, **kw) -> Signal:
    base = dict(
        id=f"g{i}",
        content=content,
        pir_ref="PIR-gen",
        timestamp=_T0 + timedelta(hours=i),
        provenance_type=ProvenanceType.primary,
        epistemic_type=EpistemicType.objective,
    )
    base.update(kw)
    return Signal(**base)


def _deception_variant(idx: int) -> Scenario:
    return Scenario(
        id=f"gen_deception_{idx}",
        decision_type=DecisionType.competitor_pricing_move,
        pir=_PIR,
        ground_truth=ScenarioGroundTruth(
            state="No change; a single trusted channel was fed a convincing planted increase rumor.",
            resolves_to="no_change",
        ),
        signal_stream=[
            _sig(
                1,
                "A normally reliable contact passes along that the competitor will raise pro-tier prices soon.",
                epistemic_type=EpistemicType.subjective,
                declared_source_reliability=SourceReliability.B,
                declared_information_credibility=InformationCredibility.four,
                supports="price_increase",
                role=SignalRole.deception,
                true_source_reliability=SourceReliability.B,
            ),
            _sig(2, "Competitor posted a backend engineering role.", supports=None, role=SignalRole.noise,
                 declared_source_reliability=SourceReliability.B,
                 declared_information_credibility=InformationCredibility.two),
        ],
        expectations=ScenarioExpectations(
            leading_hypothesis="no_change", must_resist_deception=True
        ),
    )


def _echo_variant(idx: int) -> Scenario:
    stream = [
        _sig(
            1,
            "A blogger claims the competitor will repackage tiers.",
            epistemic_type=EpistemicType.subjective,
            declared_source_reliability=SourceReliability.C,
            declared_information_credibility=InformationCredibility.three,
            supports="repackaging",
            role=SignalRole.genuine_indicator,
            true_source_reliability=SourceReliability.C,
        )
    ]
    for k in range(2, 6):
        stream.append(
            _sig(
                k,
                f"Outlet {k} repeats the repackaging claim, citing the blogger.",
                provenance_type=ProvenanceType.relaying,
                epistemic_type=EpistemicType.subjective,
                echo_of="g1",
                declared_source_reliability=SourceReliability.D,
                declared_information_credibility=InformationCredibility.three,
                supports="repackaging",
                role=SignalRole.echo,
                true_source_reliability=SourceReliability.D,
            )
        )
    return Scenario(
        id=f"gen_echo_{idx}",
        decision_type=DecisionType.competitor_pricing_move,
        pir=_PIR,
        ground_truth=ScenarioGroundTruth(
            state="One unverified repackaging claim is amplified by many outlets; no independent confirmation exists.",
            resolves_to="no_change",
        ),
        signal_stream=stream,
        expectations=ScenarioExpectations(
            leading_hypothesis="no_change", must_resist_deception=False
        ),
    )


def generate_candidates(
    n: int = 2, client: Optional[ModelClient] = None
) -> List[Scenario]:
    """Return n adversarial candidate scenarios for human review before freezing.
    """
    candidates: List[Scenario] = []
    makers = [_deception_variant, _echo_variant]
    for i in range(n):
        candidates.append(makers[i % len(makers)](i))
    return candidates
