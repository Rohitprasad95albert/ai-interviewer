"""
Single place that decides which LLMClient implementation is active.
Everything else in the app depends on the `LLMClient` protocol (app/ai/base.py)
and calls `get_llm_client()` - nothing else should import StubLLMClient or
AnthropicLLMClient directly. This is what makes swapping them a one-line
change (see spec section 23, AI Architecture).
"""

import logging

from app.ai.base import LLMClient
from app.ai.stub_client import StubLLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is not None:
        return _client

    if settings.anthropic_api_key:
        from app.ai.anthropic_client import AnthropicLLMClient

        logger.info("AI layer: using AnthropicLLMClient (model=%s)", settings.anthropic_model)
        _client = AnthropicLLMClient()
    else:
        logger.warning(
            "ANTHROPIC_API_KEY is not set - using StubLLMClient. "
            "Questions and evaluations are NOT real AI output."
        )
        _client = StubLLMClient()

    return _client


def reset_llm_client_for_tests() -> None:
    """Test-only escape hatch so tests can force a fresh client/stub."""
    global _client
    _client = None
