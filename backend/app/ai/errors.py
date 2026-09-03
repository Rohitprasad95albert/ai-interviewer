"""
Provider-agnostic LLM failure types. A concrete client (OpenRouterLLMClient
today) catches its SDK's own exceptions and translates them into these -
callers (engine.py, resume/service.py) can catch LLMProviderError without
knowing or caring which provider is behind LLMClient. Never include raw
provider response bodies or prompt/resume content in these messages - they
may end up in logs.
"""


class LLMProviderError(Exception):
    """Base class for all LLM-provider-level failures."""


class LLMAuthenticationError(LLMProviderError):
    """API key missing, invalid, or rejected."""


class LLMRateLimitError(LLMProviderError):
    """Provider rate limit or quota exceeded."""


class LLMTimeoutError(LLMProviderError):
    """Request did not complete within the configured timeout."""


class LLMConnectionError(LLMProviderError):
    """Network-level failure reaching the provider."""


class LLMInvalidResponseError(LLMProviderError):
    """
    The provider responded, but the content wasn't usable: malformed JSON,
    or valid JSON that didn't match the required schema, even after a
    corrective retry.
    """
