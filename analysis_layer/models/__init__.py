"""Model layer: the swappable interface behind which all reasoning runs.

Nothing outside this package imports a provider SDK, so a hosted frontier model
can be swapped for a self-hosted open one without touching the pipeline (PRD
Section 9.1 / Section 10).
"""

from analysis_layer.models.client import (
    AnthropicClient,
    GoogleAIClient,
    MockClient,
    ModelClient,
    build_client,
)
from analysis_layer.models.tiers import Tier

__all__ = [
    "AnthropicClient",
    "GoogleAIClient",
    "MockClient",
    "ModelClient",
    "build_client",
    "Tier",
]
