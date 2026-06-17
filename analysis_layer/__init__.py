"""Analysis Layer: a decision-anchored judgment engine.

The package implements the doctrine in analysis-layer-prd.md, Appendix A. The
control flow is a deterministic pipeline (analysis_layer.pipeline.orchestrator)
with language-model reasoning nodes inside it; code performs all arithmetic and
the model performs judgment (PRD Section 4).
"""

__version__ = "0.0.1"
