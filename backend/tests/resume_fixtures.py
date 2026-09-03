"""
Generates real, valid PDF byte fixtures for resume extraction tests, using
reportlab (test-only dependency - see requirements-dev.txt) rather than
hand-crafted PDF bytes, so the fixtures are genuinely valid PDFs and not
fragile approximations of the format.
"""

from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def make_pdf_bytes(lines: list[str]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    for line in lines:
        pdf.drawString(72, y, line)
        y -= 18
        if y < 72:
            pdf.showPage()
            y = 750
    pdf.save()
    return buffer.getvalue()


SAMPLE_RESUME_LINES = [
    "Jane Doe",
    "jane.doe@example.com",
    "",
    "EDUCATION",
    "ABC Institute of Technology - B.Tech Computer Science, 2022-2026",
    "",
    "PROJECTS",
    "AI Interviewer - Built with Python, FastAPI, and MongoDB to simulate technical interviews.",
    "Portfolio Website - Built with React and Tailwind CSS, deployed on AWS.",
    "",
    "EXPERIENCE",
    "Acme Corp - Software Engineering Intern, Summer 2025",
    "",
    "CERTIFICATIONS",
    "AWS Certified Cloud Practitioner",
    "",
    "ACHIEVEMENTS",
    "Winner, National Hackathon 2025",
]


def sample_resume_pdf_bytes() -> bytes:
    return make_pdf_bytes(SAMPLE_RESUME_LINES)


def empty_page_pdf_bytes() -> bytes:
    """A structurally valid PDF with a blank page - no extractable text."""
    return make_pdf_bytes([])


def corrupt_pdf_bytes() -> bytes:
    """Starts with a valid PDF header but the rest is garbage - simulates
    a truncated/corrupted upload."""
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nthis is not a valid pdf body at all"
