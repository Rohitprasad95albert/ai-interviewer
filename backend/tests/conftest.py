"""
Test-only setup. Points tests at a separate database so integration tests
don't pollute the "ai_interviewer" dev database with test interviews, and
forces the LLM provider to "stub" so the general test suite never depends
on - or spends credits calling - a real LLM API, regardless of what
backend/.env has configured for local dev use.

Process environment variables outrank a Settings' `env_file` in
pydantic-settings' precedence, so setting os.environ here (before anything
imports app.core.config) overrides whatever LLM_PROVIDER=... is in
backend/.env. test_openrouter_live.py deliberately bypasses this - it
constructs OpenRouterLLMClient directly rather than going through
get_llm_client()/LLM_PROVIDER, and gates itself on OPENROUTER_API_KEY
(read directly from .env, untouched by this override) instead.

Must run before app.core.config is imported anywhere, which is why this is
in conftest.py (pytest imports it before collecting test modules) rather
than inside a test file.
"""

import os

os.environ.setdefault("MONGODB_DB_NAME", "ai_interviewer_test")
os.environ["LLM_PROVIDER"] = "stub"
