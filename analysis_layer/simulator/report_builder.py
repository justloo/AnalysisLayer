"""Shared report/scoreboard result builder (Fix Spec Section 6 audit).

Every report path re-reads expectations from the scenario file on disk and
asserts harness self-consistency before rendering.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from analysis_layer.schema.assessment import Assessment
from analysis_layer.schema.signals import Scenario
from analysis_layer.simulator.harness_checks import assert_scoreboard_self_consistency
from analysis_layer.simulator.loader import load_scenario
from analysis_layer.simulator.synthetic import SyntheticResult, run_scenario


@dataclass
class ScenarioReport:
    scenario: Scenario
    result: SyntheticResult
    assessment: Assessment
    expected_leading_from_file: str
    resolves_to_from_file: str
    hypotheses_sorted: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    assumptions: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def leading_matches_expected(self) -> bool:
        return self.result.leading_hypothesis == self.expected_leading_from_file

    @property
    def expected_matches_resolves(self) -> bool:
        return self.expected_leading_from_file == self.resolves_to_from_file


def build_scenario_report(path: str | Path) -> ScenarioReport:
    """Run one scenario and build a report payload with T0 self-consistency enforced."""
    scenario_path = Path(path)
    scenario = load_scenario(scenario_path)
    result = run_scenario(scenario)
    assert_scoreboard_self_consistency(scenario, result)

    expected_from_file = scenario.expectations.leading_hypothesis
    a = result.assessment
    hyps = sorted(
        [
            {
                "id": h.id,
                "statement": h.statement,
                "status": h.status.value,
                "relative_likelihood": h.relative_likelihood,
                "is_null": h.is_null,
                "is_deception": h.is_deception,
                "rationale": h.rationale,
            }
            for h in a.hypotheses
        ],
        key=lambda x: x["relative_likelihood"],
        reverse=True,
    )
    evidence = [
        {
            "id": e.id,
            "content": e.content,
            "source_reliability": e.source_reliability.value,
            "information_credibility": e.information_credibility.value,
            "primary": e.source_type.primary,
            "objective": e.source_type.objective,
            "origin_id": e.origin_id,
            "diagnostic_value": e.diagnostic_value,
            "weak_signal": e.weak_signal,
        }
        for e in a.evidence
    ]
    assumptions = [{"statement": ass.statement, "fragility": ass.fragility} for ass in a.assumptions]

    return ScenarioReport(
        scenario=scenario,
        result=result,
        assessment=a,
        expected_leading_from_file=expected_from_file,
        resolves_to_from_file=scenario.ground_truth.resolves_to,
        hypotheses_sorted=hyps,
        evidence=evidence,
        assumptions=assumptions,
    )


def build_library_reports(
    scenario_paths: Optional[List[str | Path]] = None,
    scenarios_dir: Optional[Path] = None,
) -> List[ScenarioReport]:
    directory = scenarios_dir or Path(__file__).parent / "scenarios"
    if scenario_paths is None:
        paths = sorted(directory.glob("*.json"))
    else:
        paths = [Path(p) for p in scenario_paths]
    return [build_scenario_report(p) for p in paths]


def report_to_dict(report: ScenarioReport) -> Dict[str, Any]:
    """JSON-serializable summary for HTML/Markdown generators."""
    a = report.assessment
    return {
        "id": report.scenario.id,
        "pir": report.scenario.pir,
        "ground_truth_state": report.scenario.ground_truth.state,
        "ground_truth_resolves_to": report.resolves_to_from_file,
        "passed": report.result.passed,
        "leading_hypothesis": report.result.leading_hypothesis,
        "expected_leading": report.expected_leading_from_file,
        "bluf": a.bluf,
        "likelihood": {
            "term": a.likelihood.term.value,
            "low": a.likelihood.probability_band.low,
            "high": a.likelihood.probability_band.high,
        },
        "confidence": {
            "level": a.confidence.level.value,
            "low": a.confidence.band.low,
            "high": a.confidence.band.high,
            "drivers": a.confidence.drivers,
        },
        "key_judgments": a.key_judgments,
        "recommended_action": a.recommended_action,
        "hypotheses": report.hypotheses_sorted,
        "evidence": report.evidence,
        "assumptions": report.assumptions,
        "gaps": a.gaps,
        "red_team": {
            "outcome": a.red_team.outcome.value,
            "challenges_raised": a.red_team.challenges_raised,
        },
    }
