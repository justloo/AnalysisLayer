"""The swappable model interface.

`ModelClient.reason(task, payload, tier)` is the single entry point every
reasoning node uses. The pipeline depends only on this interface, so a hosted
frontier model can be swapped for a self-hosted open one without touching the
pipeline (PRD Section 9.1 / Section 10).
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional

from analysis_layer.config import Settings, get_settings
from analysis_layer.models import mock_reasoner, prompts
from analysis_layer.models.tiers import Tier, model_for_tier


class ModelClient(ABC):
    """Reason about a structured task and return a structured (dict) result."""

    @abstractmethod
    def reason(self, task: str, payload: Dict, tier: Tier = Tier.fast) -> Dict:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return type(self).__name__


class MockClient(ModelClient):
    """Deterministic, offline backend. Dispatches to mock_reasoner handlers."""

    def reason(self, task: str, payload: Dict, tier: Tier = Tier.fast) -> Dict:
        return mock_reasoner.handle(task, payload)


class GoogleAIClient(ModelClient):
    """Google AI Studio / Gemini Developer API (google-genai SDK).

    Get an API key at https://aistudio.google.com/apikey. Imported lazily so the
    offline harness never requires the SDK to be installed.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - exercised only with extra
            raise RuntimeError(
                "The 'google' extra is not installed. Install with "
                "`pip install \"google-genai>=1.0\"` or set "
                "ANALYSIS_LAYER_MODEL_BACKEND=mock."
            ) from exc

        api_key = self.settings.google_api_key or None
        if api_key is None and not (
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        ):
            raise RuntimeError(
                "GOOGLE_API_KEY or GEMINI_API_KEY is not set. "
                "Create a key at https://aistudio.google.com/apikey"
            )
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self._types = types

    def reason(self, task: str, payload: Dict, tier: Tier = Tier.fast) -> Dict:
        system = prompts.system_prompt_for(task)
        model = model_for_tier(tier, self.settings)
        user = (
            "Task: " + task + "\n"
            "Input (JSON):\n" + json.dumps(payload, default=str) + "\n\n"
            "Respond with ONLY a JSON object."
        )
        text = self._complete(system, user, model)
        try:
            return _extract_json(text)
        except ValueError:
            repair = user + "\n\nYour previous reply was not valid JSON. Reply with ONLY JSON."
            text = self._complete(system, repair, model)
            return _extract_json(text)

    def _complete(self, system: str, user: str, model: str) -> str:
        response = self._client.models.generate_content(
            model=model,
            contents=user,
            config=self._types.GenerateContentConfig(
                system_instruction=system,
                temperature=self.settings.temperature,
                max_output_tokens=2048,
                response_mime_type="application/json",
            ),
        )
        return response.text or ""


class AnthropicClient(ModelClient):
    """Legacy Anthropic provider. Imported lazily so the offline harness never
    requires the SDK to be installed."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:  # pragma: no cover - exercised only with extra
            raise RuntimeError(
                "The 'anthropic' extra is not installed. Install with "
                "`pip install \"anthropic>=0.39\"` or set "
                "ANALYSIS_LAYER_MODEL_BACKEND=mock."
            ) from exc
        if not self.settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    def reason(self, task: str, payload: Dict, tier: Tier = Tier.fast) -> Dict:
        system = prompts.system_prompt_for(task)
        model = model_for_tier(tier, self.settings)
        user = (
            "Task: " + task + "\n"
            "Input (JSON):\n" + json.dumps(payload, default=str) + "\n\n"
            "Respond with ONLY a JSON object."
        )
        text = self._complete(system, user, model)
        try:
            return _extract_json(text)
        except ValueError:
            repair = user + "\n\nYour previous reply was not valid JSON. Reply with ONLY JSON."
            text = self._complete(system, repair, model)
            return _extract_json(text)

    def _complete(self, system: str, user: str, model: str) -> str:
        message = self._client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=self.settings.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        return "\n".join(parts)


def _extract_json(text: str) -> Dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[len("json") :]
        text = text.strip().rstrip("`").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in model response.")
    return json.loads(text[start : end + 1])


def build_client(settings: Optional[Settings] = None) -> ModelClient:
    """Construct the configured backend (mock by default, per Section 9.2)."""
    settings = settings or get_settings()
    backend = settings.model_backend.lower()
    if backend in ("google", "gemini", "google_ai"):
        return GoogleAIClient(settings)
    if backend == "anthropic":
        return AnthropicClient(settings)
    if backend == "mock":
        return MockClient()
    raise ValueError(
        f"Unknown model backend: {settings.model_backend!r}. "
        "Use mock, google, or anthropic."
    )
