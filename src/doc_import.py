"""
Document import for ShallotT.
Extracts text from .txt, .srt, .pdf, and .docx files dropped onto the translator.
"""

import os


def extract_text(filepath: str) -> tuple[str | None, str | None]:
    """Extract text content from a document.

    Returns (text, error_message).  One of them is always None.
    """
    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".txt":
            return _extract_txt(filepath), None

        elif ext == ".srt":
            return _extract_srt(filepath), None

        elif ext == ".pdf":
            return _extract_pdf(filepath), None

        elif ext == ".docx":
            return _extract_docx(filepath), None

        else:
            return None, f"Unsupported format: {ext}"

    except Exception as e:
        return None, str(e)


def _extract_txt(path: str) -> str:
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode text file")


def _extract_srt(path: str) -> str:
    """Strip SRT timestamps and index numbers, keep only dialogue."""
    import re
    raw = _extract_txt(path)
    # Remove index numbers and timestamps
    cleaned = re.sub(r'^\d+\s*$', '', raw, flags=re.MULTILINE)
    cleaned = re.sub(
        r'^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}\s*$',
        '', cleaned, flags=re.MULTILINE
    )
    # Collapse empty lines
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines)


def _extract_pdf(path: str) -> str:
    """Extract text from PDF using PyPDF2 (lightweight, pure Python)."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError(
            "PyPDF2 is required for PDF import. Install with: pip install PyPDF2"
        )

    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _extract_docx(path: str) -> str:
    """Extract text from .docx using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "python-docx is required for .docx import. Install with: pip install python-docx"
        )

    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)
