"""
Single place that decides which LLMClient implementation is active.
Everything else in the app depends on the `LLMClient` protocol
(app/ai/base.py) and calls `get_llm_client()` - nothing else should import
StubLLMClient, AnthropicLLMClient, or OpenRouterLLMClient directly. This is
what makes swapping providers a config change, not a code change (see spec
section 23, AI Architecture).

Selection is controlled by LLM_PROVIDER (see Settings.llm_provider for the
full doc). "auto" preserves the original zero-config behavior from before
OpenRouter existed (Anthropic if configured, else the stub) so existing
deployments and tests are unaffected by this option's addition.
"""

import logging

from app.ai.base import LLMClient
from app.ai.stub_client import StubLLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: LLMClient | None = None


class LLMConfigurationError(Exception):
    """Raised at startup when LLM_PROVIDER names a provider whose required
    key isn't set - fails loudly rather than silently falling back to the
    stub, so a typo'd or forgotten key is obvious immediately."""


def _build_client(provider: str) -> LLMClient:
    if provider == "openrouter":
        if not settings.openrouter_api_key:
            raise LLMConfigurationError(
                "LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is not set."
            )
        from app.ai.openrouter_client import OpenRouterLLMClient

        logger.info(
            "AI layer: using OpenRouterLLMClient (model=%s)", settings.openrouter_model
        )
        return OpenRouterLLMClient()

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LLMConfigurationError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set."
            )
        from app.ai.anthropic_client import AnthropicLLMClient

        logger.info("AI layer: using AnthropicLLMClient (model=%s)", settings.anthropic_model)
        return AnthropicLLMClient()

    if provider == "stub":
        logger.info("AI layer: using StubLLMClient (LLM_PROVIDER=stub, forced).")
        return StubLLMClient()

    if provider == "auto":
        if settings.anthropic_api_key:
            from app.ai.anthropic_client import AnthropicLLMClient

            logger.info(
                "AI layer: using AnthropicLLMClient (model=%s, auto-selected)",
                settings.anthropic_model,
            )
            return AnthropicLLMClient()

        logger.warning(
            "No LLM_PROVIDER set and ANTHROPIC_API_KEY is not set - using StubLLMClient. "
            "Questions and evaluations are NOT real AI output."
        )
        return StubLLMClient()

    raise LLMConfigurationError(
        f"Unknown LLM_PROVIDER '{provider}'. Expected one of: auto, stub, anthropic, openrouter."
    )


def get_llm_client() -> LLMClient:
    global _client
    if _client is not None:
        return _client

    _client = _build_client(settings.llm_provider.lower())
    return _client


def reset_llm_client_for_tests() -> None:
    """Test-only escape hatch so tests can force a fresh client/stub."""
    global _client
    _client = None
