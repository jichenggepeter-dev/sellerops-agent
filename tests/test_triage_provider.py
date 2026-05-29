from __future__ import annotations

import pytest

from app.api.config import reset_settings_cache
from app.api.services.triage import MockTriageProvider
from app.api.services.triage_registry import get_triage_provider


def test_default_triage_provider_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SELLEROPS_TRIAGE_PROVIDER", raising=False)
    reset_settings_cache()

    provider = get_triage_provider()

    assert isinstance(provider, MockTriageProvider)
    reset_settings_cache()


def test_unsupported_triage_provider_fails_clearly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SELLEROPS_TRIAGE_PROVIDER", "unknown")
    reset_settings_cache()

    with pytest.raises(ValueError, match="Unsupported triage provider"):
        get_triage_provider()

    reset_settings_cache()


def test_openai_provider_without_key_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SELLEROPS_TRIAGE_PROVIDER", "openai")
    monkeypatch.setenv("SELLEROPS_TRIAGE_FALLBACK_TO_MOCK", "true")
    monkeypatch.delenv("SELLEROPS_OPENAI_API_KEY", raising=False)
    reset_settings_cache()

    provider = get_triage_provider()

    assert isinstance(provider, MockTriageProvider)
    reset_settings_cache()


def test_openai_provider_without_key_can_fail_strictly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SELLEROPS_TRIAGE_PROVIDER", "openai")
    monkeypatch.setenv("SELLEROPS_TRIAGE_FALLBACK_TO_MOCK", "false")
    monkeypatch.delenv("SELLEROPS_OPENAI_API_KEY", raising=False)
    reset_settings_cache()

    with pytest.raises(ValueError, match="SELLEROPS_OPENAI_API_KEY"):
        get_triage_provider()

    reset_settings_cache()
