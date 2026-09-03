import pytest

from app.resume.validation import ResumeValidationError, validate_upload
from tests.resume_fixtures import sample_resume_pdf_bytes


def test_accepts_a_valid_pdf():
    validate_upload(content_type="application/pdf", file_bytes=sample_resume_pdf_bytes())
    # No exception raised = pass


def test_rejects_non_pdf_content_type():
    with pytest.raises(ResumeValidationError, match="Unsupported file type"):
        validate_upload(content_type="image/png", file_bytes=b"whatever")


def test_rejects_missing_content_type():
    with pytest.raises(ResumeValidationError):
        validate_upload(content_type=None, file_bytes=b"whatever")


def test_rejects_empty_file():
    with pytest.raises(ResumeValidationError, match="empty"):
        validate_upload(content_type="application/pdf", file_bytes=b"")


def test_rejects_oversized_file():
    from app.core.config import settings

    too_big = b"%PDF-" + b"0" * (settings.max_resume_size_bytes + 1)
    with pytest.raises(ResumeValidationError, match="too large"):
        validate_upload(content_type="application/pdf", file_bytes=too_big)


def test_rejects_mislabeled_file_missing_pdf_magic_bytes():
    # Claims to be a PDF via content-type, but the bytes say otherwise -
    # this is exactly the case where trusting content-type alone would be
    # wrong.
    with pytest.raises(ResumeValidationError, match="doesn't look like a valid PDF"):
        validate_upload(content_type="application/pdf", file_bytes=b"this is actually plain text")
