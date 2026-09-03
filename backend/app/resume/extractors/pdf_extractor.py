"""
Deterministic PDF -> text extraction via pypdf. No LLM involved - this is
exactly the kind of extraction spec Milestone 4 requires to be reliable and
non-AI-dependent, since a resume upload must not silently fail just because
an API key is missing or a model call errors.
"""

import logging

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.resume.extractors.base import ExtractionError, TextExtractor

logger = logging.getLogger(__name__)


class PdfTextExtractor(TextExtractor):
    def extract(self, file_bytes: bytes) -> str:
        from io import BytesIO

        try:
            reader = PdfReader(BytesIO(file_bytes))
        except (PdfReadError, ValueError) as exc:
            # Log only the exception type, never str(exc) - pypdf's parser
            # errors can include raw bytes from the file being parsed.
            logger.warning("PDF parsing failed: %s", type(exc).__name__)
            raise ExtractionError("Could not read this PDF - it may be corrupted.") from exc

        if reader.is_encrypted:
            # pypdf can sometimes open encrypted PDFs with an empty owner
            # password, but we don't attempt password guessing.
            try:
                if reader.decrypt("") == 0:
                    raise ExtractionError("This PDF is password-protected.")
            except Exception as exc:
                raise ExtractionError("This PDF is password-protected.") from exc

        try:
            pages_text = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:  # noqa: BLE001 - pypdf can raise various internal errors on malformed content streams
            logger.warning("PDF text extraction failed: %s", type(exc).__name__)
            raise ExtractionError("Could not extract text from this PDF.") from exc

        text = "\n".join(pages_text).strip()
        if not text:
            raise ExtractionError(
                "No extractable text found - this PDF may be a scanned image without OCR."
            )
        return text
