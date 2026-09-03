"""
Loads prompt templates from the top-level prompts/ directory (spec section
25: "keep AI prompts separate from application code"). Templates are plain
text with {placeholder} slots - deliberately simple string formatting, not a
templating engine, since the prompts are short and reviewed by hand.

prompts/ lives at the repo root (sibling to backend/), not inside the
backend Python package, so it's just as easy for a non-Python-fluent reader
to find and edit prompt wording without touching app code.
"""

from functools import lru_cache
from pathlib import Path

# backend/app/ai/prompts.py -> parents[2] is the backend/ dir's parent, i.e.
# the repo root (ai-interviewer/).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROMPTS_DIR = _REPO_ROOT / "prompts"


@lru_cache
def load_prompt(*parts: str) -> str:
    path = _PROMPTS_DIR.joinpath(*parts)
    return path.read_text(encoding="utf-8")
