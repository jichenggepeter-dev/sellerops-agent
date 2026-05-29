"""Triage provider registry."""

from __future__ import annotations

from app.api.config import get_settings
from app.api.services.openai_triage import OpenAITriageProvider
from app.api.services.triage import MockTriageProvider, TriageProvider


def get_triage_provider() -> TriageProvider:
    settings = get_settings()
    provider = settings.triage_provider
    if provider == "mock":
        return MockTriageProvider()
    if provider == "openai":
        try:
            return OpenAITriageProvider()
        except ValueError:
            if settings.triage_fallback_to_mock:
                return MockTriageProvider()
            raise
    raise ValueError(f"Unsupported triage provider: {provider}")
