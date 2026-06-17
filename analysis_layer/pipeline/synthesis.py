"""FR-11, Synthesis into the assessment object (PRD A3.11).

Produce the decision-ready product in BLUF form: bottom line first, then key
judgments, graded evidence, the hypothesis set with statuses, assumptions, gaps,
the separate likelihood and confidence fields, a recommended action framed as a
decision input (R20), and an indicators-and-warning watch list whose entries
carry explicit resolution criteria (R17). The watch list is what makes the layer
predictive rather than a rearview mirror.
"""
from __future__ import annotations

from analysis_layer.models import tasks
from analysis_layer.models.client import ModelClient
from analysis_layer.models.tiers import Tier
from analysis_layer.schema.assessment import (
    Assessment,
    Calibration,
    CalibrationStatus,
    IndicatorDirection,
    IndicatorWatch,
)
from analysis_layer.schema.state import AnalysisState

_MATERIAL_IDS = {"price_cut", "price_increase", "repackaging"}


def synthesize(state: AnalysisState, client: ModelClient) -> Assessment:
    leading = state.hypothesis(state.leading_hypothesis_id) if state.leading_hypothesis_id else None
    leading_statement = leading.statement if leading else "No material change is expected."
    likelihood = state.likelihood
    likelihood_phrase = likelihood.rendered() if likelihood else "roughly even chance"

    res = client.reason(
        tasks.SYNTHESIZE,
        {
            "leading_hypothesis_id": state.leading_hypothesis_id,
            "leading_statement": leading_statement,
            "likelihood_phrase": likelihood.term.value if likelihood else "roughly even chance",
            "top_gap": state.gaps[0] if state.gaps else None,
        },
        Tier.strong,
    )

    _add_standard_watch_indicators(state)
    forecast_probability = (
        state.posteriors.get(state.leading_hypothesis_id, 0.5)
        if state.leading_hypothesis_id
        else 0.5
    )

    calibration = Calibration(
        resolvable_claim=_resolvable_claim(state, leading_statement),
        status=CalibrationStatus.open,
        forecast_probability=round(forecast_probability, 4),
    )

    return Assessment(
        id=state.event_id,
        pir_ref=state.pir_ref,
        bluf=res.get("bluf", leading_statement),
        likelihood=likelihood,
        confidence=state.confidence,
        key_judgments=res.get("key_judgments", [leading_statement]),
        evidence=state.evidence,
        hypotheses=state.hypotheses,
        assumptions=state.assumptions,
        gaps=state.gaps,
        indicators_watch=state.indicators_watch,
        recommended_action=res.get("recommended_action", ""),
        red_team=state.red_team,
        human_overrides=[],
        calibration=calibration,
    )


def _resolvable_claim(state: AnalysisState, leading_statement: str) -> str:
    if state.leading_hypothesis_id in _MATERIAL_IDS:
        return (
            f"Within 30 days, the tracked competitor makes the move: {leading_statement} "
            "Resolved by an observed, dated public pricing change."
        )
    return (
        "Within 30 days, the tracked competitor makes no material pricing change. "
        "Resolved by the absence of any observed public pricing change in the window."
    )


def _add_standard_watch_indicators(state: AnalysisState) -> None:
    leading = state.leading_hypothesis_id
    if leading in _MATERIAL_IDS:
        state.indicators_watch.append(
            IndicatorWatch(
                indicator="Public pricing-page edit on the tracked product line.",
                direction=IndicatorDirection.confirms,
                resolution_criterion="The competitor's public pricing page shows a changed price within the window.",
            )
        )
        state.indicators_watch.append(
            IndicatorWatch(
                indicator="Window closes with no observed pricing change.",
                direction=IndicatorDirection.breaks,
                resolution_criterion="No public pricing change is observed by the 30-day window close.",
            )
        )
    else:
        state.indicators_watch.append(
            IndicatorWatch(
                indicator="Any public pricing-page edit before the window closes.",
                direction=IndicatorDirection.breaks,
                resolution_criterion="A public pricing change is observed within the window.",
            )
        )
