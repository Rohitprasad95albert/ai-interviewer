import pytest

from app.resume.extractors.base import ExtractionError
from app.resume.extractors.pdf_extractor import PdfTextExtractor
from tests.resume_fixtures import (
    corrupt_pdf_bytes,
    empty_page_pdf_bytes,
    sample_resume_pdf_bytes,
)


def test_extracts_text_from_a_valid_pdf():
    text = PdfTextExtractor().extract(sample_resume_pdf_bytes())
    assert "Jane Doe" in text
    assert "EDUCATION" in text
    assert "AWS Certified Cloud Practitioner" in text


def test_raises_extraction_error_on_corrupt_pdf():
    with pytest.raises(ExtractionError):
        PdfTextExtractor().extract(corrupt_pdf_bytes())


def test_extraction_error_message_does_not_leak_raw_exception_text():
    # The message must be a safe, generic, pre-written string - never the
    # underlying parser's own error text, which can echo file bytes.
    try:
        PdfTextExtractor().extract(corrupt_pdf_bytes())
        pytest.fail("expected ExtractionError")
    except ExtractionError as exc:
        assert str(exc) == "Could not read this PDF - it may be corrupted."


def test_raises_extraction_error_on_blank_page_with_no_text():
    with pytest.raises(ExtractionError, match="No extractable text"):
        PdfTextExtractor().extract(empty_page_pdf_bytes())


def test_raises_extraction_error_on_garbage_bytes():
    with pytest.raises(ExtractionError):
        PdfTextExtractor().extract(b"not a pdf at all, just random bytes")
