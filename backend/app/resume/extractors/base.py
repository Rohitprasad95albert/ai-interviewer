"""
Text-extraction interface, deliberately separate from the LLMClient
interface in app/ai/base.py - this is plain deterministic file parsing, no
model involved. Adding DOCX support later means adding a docx_extractor.py
implementing this same protocol and one line in get_extractor(); nothing
else in the resume pipeline changes.
"""

from typing import Protocol


class ExtractionError(Exception):
    """
    Raised when a file can't be parsed into text - a corrupt/malformed
    file, an encrypted PDF, an empty document, etc. The message must be
    generic (spec: never expose private resume contents in errors/logs) -
    never include raw exception text from the underlying parser, which can
    echo fragments of file content.
    """


class TextExtractor(Protocol):
    def extract(self, file_bytes: bytes) -> str:
        """Return the extracted plain text, or raise ExtractionError."""
        ...


class UnsupportedFileTypeError(Exception):
    pass


def get_extractor(content_type: str) -> TextExtractor:
    if content_type == "application/pdf":
        from app.resume.extractors.pdf_extractor import PdfTextExtractor

        return PdfTextExtractor()
    # DOCX support (spec section 6: "DOCX resume if practical") slots in
    # here later: elif content_type == DOCX_MIME: return DocxTextExtractor()
    raise UnsupportedFileTypeError(content_type)
