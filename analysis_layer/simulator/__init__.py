"""The simulator: the six-mode test rig that makes the layer testable.

Its design reuses the live calibration machinery, so the test rig and the
production monitor are the same system fed different outcomes (PRD Section 7).
"""

from analysis_layer.simulator.loader import (
    DEFAULT_LIBRARY_DIR,
    load_library,
    load_scenario,
)
from analysis_layer.simulator.synthetic import SyntheticResult, run_scenario

__all__ = [
    "DEFAULT_LIBRARY_DIR",
    "load_library",
    "load_scenario",
    "SyntheticResult",
    "run_scenario",
]
