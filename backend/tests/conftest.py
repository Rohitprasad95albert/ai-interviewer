"""
Test-only setup. Points tests at a separate database so integration tests
don't pollute the "ai_interviewer" dev database with test interviews.

Must run before app.core.config is imported anywhere, which is why this is
in conftest.py (pytest imports it before collecting test modules) rather
than inside a test file.
"""

import os

os.environ.setdefault("MONGODB_DB_NAME", "ai_interviewer_test")
