# Analysis Layer

A decision-anchored **judgment engine**. It receives a stream of signals and
produces decision-ready, confidence-scored, auditable assessments. It is
tool-agnostic: it sits on top of any collection source and automates the senior
analyst's judgment, not the junior analyst's clipping.

This repository implements the doctrine in
[analysis-layer-prd.md](analysis-layer-prd.md) (Appendix A is canonical). v0 is
anchored on one decision type, **competitor pricing-move early warning**, and is
built to be testable from the first functional milestone.

## What this is, technically

A deterministic pipeline with language-model reasoning nodes inside it (PRD
Section 4). Code performs orchestration and all arithmetic (diagnosticity,
confidence, likelihood lookup, calibration); the model performs judgment
(hypothesis generation, per-cell consistency, the red-team challenge,
synthesis). The control flow is **not** an autonomous agent that picks its own
path; the stage order is enforced so no judgment can skip grading, hypothesis
testing, or adversarial review (R3).

```
signals -> intake -> cluster -> grade -> weight (relay collapse)
        -> hypotheses -> matrix -> disconfirmation -> assumptions/gaps
        -> red team (can BLOCK) -> confidence -> likelihood -> synthesis
        -> aggregate -> calibration
```

## Quick start (offline, no API keys)

By default the reasoning nodes are backed by a deterministic mock, the store is
in-memory, and nothing external is required.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # or: pip install -r requirements.txt
pytest                      # run the harness: fixtures, invariants, scenarios
python cli.py run analysis_layer/simulator/scenarios/price_cut_clean.json
python cli.py score         # run the seed library and print the scoreboard
```

## Using Google AI Studio (Gemini)

Copy `.env.example` to `.env`, set `ANALYSIS_LAYER_MODEL_BACKEND=google`, add
your API key, and install the extra:

```bash
pip install -e ".[google]"
```

Get an API key at [Google AI Studio](https://aistudio.google.com/apikey). Set
either `GOOGLE_API_KEY` or `GEMINI_API_KEY`. The strong/fast model IDs are
config (`ANALYSIS_LAYER_STRONG_MODEL`, `ANALYSIS_LAYER_FAST_MODEL`), never code,
so a provider/model swap never touches the pipeline (Section 9.1).

Default tiers: `gemini-2.5-pro` (strong) and `gemini-2.5-flash` (fast).

## Using Anthropic (optional alternative)

```bash
# In .env: ANALYSIS_LAYER_MODEL_BACKEND=anthropic, ANTHROPIC_API_KEY=...
pip install -e ".[anthropic]"
```

## Postgres calibration store (optional)

```bash
docker compose up -d
pip install -e ".[postgres]"
export ANALYSIS_LAYER_STORE_BACKEND=postgres
```

## Layout

```
analysis_layer/
  pipeline/      # the ordered stages (FR-1..FR-12) + orchestrator (R3)
  models/        # the swappable model interface, tiers, prompts, mock
  schema/        # the assessment contract (Section 6) + pipeline state
  calibration/   # store (memory/postgres) + Brier/curve scoring (FR-13)
  simulator/     # six-mode harness + frozen scenario library (Section 7)
tests/           # Mode 1 deterministic fixtures + invariant + scenario tests
cli.py           # the v0 runner
```

The package directory uses `analysis_layer` (an underscore) so it is importable;
it is the `analysis-layer/` tree from PRD Section 9.3.

## The simulator (how it becomes testable)

Six modes, all building on `pytest` and sharing the live calibration machinery
(test rig and production monitor are the same system):

1. **Deterministic fixtures** — code nodes as ordinary unit tests.
2. **Invariants** — pass-or-fail gates on every run (null always present, echo
   is not corroboration, weak signals escalated, likelihood/confidence kept
   separate, the red team can block). These map to R5, R6, R7, R13, R16.
3. **Reference cases** — closeness scoring against an analyst gold standard.
4. **Synthetic scenarios** — authored ground truth + a declared signal stream;
   the core of the rig and where most failure-mode testing lives.
5. **Backtesting** — resolved history replayed with lookahead-leakage defenses.
6. **Shadow** — a deployment mode that logs beside a human/incumbent.

The scoreboard reports a calibration curve, Brier score, and resolution per
segment over a distribution of runs (Section 7.8), not a single green check.
