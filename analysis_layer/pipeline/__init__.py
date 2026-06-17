"""The analytic pipeline: a fixed, ordered sequence of stages (PRD A3).

The discipline is the point. The engine must not be able to emit a judgment that
skipped grading, hypothesis testing, or adversarial review (R3). Order is
enforced by analysis_layer.pipeline.orchestrator.
"""

from analysis_layer.pipeline.orchestrator import Orchestrator, run_pipeline

__all__ = ["Orchestrator", "run_pipeline"]
