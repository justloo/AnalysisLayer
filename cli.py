"""The v0 command-line runner (PRD Section 9.2).

The shortest path to running the layer: execute the pipeline on a scenario file
and print the assessment, or run the seed library and print the scoreboard. No
HTTP API and no task queue are needed at this stage.

Usage:
  python cli.py run <scenario.json>      # run one scenario, print the assessment
  python cli.py score [--runs N]         # run the seed library, print scoreboard
  python cli.py invariants               # run invariants over the seed library
  python cli.py generate [--n N]         # emit adversarial candidate scenarios
"""
from __future__ import annotations

import argparse
import json
import sys

from analysis_layer.simulator.invariants import run_all_invariants
from analysis_layer.simulator.loader import load_library, load_scenario
from analysis_layer.simulator.scoreboard import render, run_scoreboard
from analysis_layer.simulator.synthetic import run_scenario


def _cmd_run(args: argparse.Namespace) -> int:
    scenario = load_scenario(args.scenario)
    result = run_scenario(scenario)
    a = result.assessment
    print(json.dumps(json.loads(a.model_dump_json()), indent=2, default=str))
    print("\n--- summary ---", file=sys.stderr)
    print(f"leading: {result.leading_hypothesis} (expected {result.expected_leading})", file=sys.stderr)
    print(f"likelihood: {a.likelihood.rendered()}", file=sys.stderr)
    print(f"confidence: {a.confidence.level.value} {a.confidence.band}", file=sys.stderr)
    print(f"red team: {a.red_team.outcome.value}", file=sys.stderr)
    print(f"scenario PASS: {result.passed}", file=sys.stderr)
    return 0 if result.passed else 1


def _cmd_score(args: argparse.Namespace) -> int:
    sb = run_scoreboard(runs=args.runs)
    print(render(sb))
    return 0 if sb.passes() else 1


def _cmd_invariants(_args: argparse.Namespace) -> int:
    ok = True
    for sc in load_library():
        result = run_scenario(sc)
        for inv in run_all_invariants(sc, result.assessment):
            status = "PASS" if inv.passed else "FAIL"
            if not inv.passed:
                ok = False
            print(f"[{status}] {sc.id:22} {inv.name}{(' - ' + inv.detail) if inv.detail and not inv.passed else ''}")
    print("\nINVARIANTS:", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


def _cmd_generate(args: argparse.Namespace) -> int:
    from analysis_layer.simulator.generator import generate_candidates

    for sc in generate_candidates(args.n):
        print(sc.model_dump_json(indent=2))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="analysis-layer", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run one scenario and print the assessment")
    p_run.add_argument("scenario")
    p_run.set_defaults(func=_cmd_run)

    p_score = sub.add_parser("score", help="run the seed library and print the scoreboard")
    p_score.add_argument("--runs", type=int, default=5)
    p_score.set_defaults(func=_cmd_score)

    p_inv = sub.add_parser("invariants", help="run invariants over the seed library")
    p_inv.set_defaults(func=_cmd_invariants)

    p_gen = sub.add_parser("generate", help="emit adversarial candidate scenarios")
    p_gen.add_argument("--n", type=int, default=2)
    p_gen.set_defaults(func=_cmd_generate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
