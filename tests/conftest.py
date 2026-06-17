"""Shared fixtures for the harness."""
from __future__ import annotations

import pytest

from analysis_layer.config import get_settings
from analysis_layer.models.client import MockClient
from analysis_layer.simulator.loader import load_library


@pytest.fixture
def client():
    return MockClient()


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def library():
    return load_library()
