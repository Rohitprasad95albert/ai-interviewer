"""
Upload validation - runs before any parsing. Two independent checks on file
type (declared content-type AND magic bytes) because a client can lie about
content-type, and we'd rather reject a mislabeled file cleanly than hand it
to a parser expecting a different format.
"""

from app.core.config import settings

PDF_MAGIC_BYTES = b"%PDF-"
ALLOWED_CONTENT_TYPES = {"application/pdf"}


class ResumeValidationError(Exception):
    """User-facing validation failure - message is always safe to return as-is."""


def validate_upload(*, content_type: str | None, file_bytes: bytes) -> None:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ResumeValidationError(
            f"Unsupported file type '{content_type}'. Only PDF is supported right now."
        )

    if not file_bytes:
        raise ResumeValidationError("The uploaded file is empty.")

    if len(file_bytes) > settings.max_resume_size_bytes:
        max_mb = settings.max_resume_size_bytes / (1024 * 1024)
        raise ResumeValidationError(f"File is too large - the limit is {max_mb:.0f}MB.")

    if not file_bytes.startswith(PDF_MAGIC_BYTES):
        raise ResumeValidationError(
            "This file doesn't look like a valid PDF (missing PDF header)."
        )
