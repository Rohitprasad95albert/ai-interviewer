"""
app/ai/factory.py provider-selection tests. Uses monkeypatch on the live
`settings` singleton (Pydantic models are mutable unless frozen) rather than
environment variables, since Settings is already loaded and cached by the
time tests run.
"""

import pytest

from app.ai.factory import LLMConfigurationError, get_llm_client, reset_llm_client_for_tests
from app.ai.stub_client import StubLLMClient
from app.core.config import settings


@pytest.fixture(autouse=True)
def _reset_client_cache():
    reset_llm_client_for_tests()
    yield
    reset_llm_client_for_tests()


def test_auto_mode_uses_stub_when_no_keys_set(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "auto")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    client = get_llm_client()

    assert isinstance(client, StubLLMClient)


def test_explicit_stub_provider_forces_stub_even_with_keys_set(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "stub")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-fake")

    client = get_llm_client()

    assert isinstance(client, StubLLMClient)


def test_openrouter_provider_without_key_raises_configuration_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "")

    with pytest.raises(LLMConfigurationError, match="OPENROUTER_API_KEY"):
        get_llm_client()


def test_openrouter_provider_with_key_builds_openrouter_client(monkeypatch):
    from app.ai.openrouter_client import OpenRouterLLMClient

    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-or-fake-for-test")

    client = get_llm_client()

    assert isinstance(client, OpenRouterLLMClient)


def test_anthropic_provider_without_key_raises_configuration_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", "")

    with pytest.raises(LLMConfigurationError, match="ANTHROPIC_API_KEY"):
        get_llm_client()


def test_unknown_provider_raises_configuration_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "not-a-real-provider")

    with pytest.raises(LLMConfigurationError, match="Unknown LLM_PROVIDER"):
        get_llm_client()


def test_client_is_cached_across_calls(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "stub")

    first = get_llm_client()
    second = get_llm_client()

    assert first is second


def test_openrouter_model_is_read_from_settings_not_hardcoded(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-or-fake-for-test")
    monkeypatch.setattr(settings, "openrouter_model", "some/custom-model-slug")

    client = get_llm_client()

    assert client._model == "some/custom-model-slug"
