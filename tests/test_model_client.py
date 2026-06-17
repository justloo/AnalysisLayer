"""Model provider wiring tests."""
from __future__ import annotations

import os

import pytest

from analysis_layer.config import Settings, reset_settings_cache
from analysis_layer.models.client import GoogleAIClient, MockClient, build_client


def test_mock_backend_is_default():
    reset_settings_cache()
    os.environ.pop("ANALYSIS_LAYER_MODEL_BACKEND", None)
    client = build_client()
    assert isinstance(client, MockClient)
    reset_settings_cache()


def test_google_backend_builds_client_when_configured(monkeypatch):
    pytest.importorskip("google.genai")
    reset_settings_cache()
    monkeypatch.setenv("ANALYSIS_LAYER_MODEL_BACKEND", "google")
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-test-key")
    client = build_client()
    assert isinstance(client, GoogleAIClient)
    reset_settings_cache()


def test_google_client_requires_api_key():
    pytest.importorskip("google.genai")
    reset_settings_cache()
    settings = Settings(
        model_backend="google",
        google_api_key="",
        strong_model="gemini-2.5-pro",
        fast_model="gemini-2.5-flash",
    )
    # Clear env keys the SDK might read.
    for key in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
        os.environ.pop(key, None)
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY|GEMINI_API_KEY"):
        GoogleAIClient(settings)
    reset_settings_cache()
