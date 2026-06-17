"""Load scenarios from the frozen library (PRD Section 7.7 / 9.3)."""
from __future__ import annotations

from pathlib import Path
from typing import List

from analysis_layer.schema.signals import Scenario

DEFAULT_LIBRARY_DIR = Path(__file__).parent / "scenarios"


def load_scenario(path: str | Path) -> Scenario:
    return Scenario.model_validate_json(Path(path).read_text())


def load_library(directory: str | Path = DEFAULT_LIBRARY_DIR) -> List[Scenario]:
    directory = Path(directory)
    scenarios = [load_scenario(p) for p in sorted(directory.glob("*.json"))]
    return scenarios
