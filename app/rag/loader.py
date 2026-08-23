"""
PDF loader module.
Responsible for reading a PDF file and extracting raw text from it,
page by page, using PyMuPDF (imported as 'fitz').
"""

import fitz  # PyMuPDF
from app.logger import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from a PDF file, page by page.

    Args:
        pdf_path: Absolute path to the PDF file on disk.

    Returns:
        A list of dicts, one per page, in the form:
        [
            {"page_number": 1, "text": "..."},
            {"page_number": 2, "text": "..."},
            ...
        ]

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the PDF has no extractable text at all
                    (e.g. a scanned/image-only PDF).
    """
    logger.info(f"Starting text extraction for: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Failed to open PDF: {pdf_path} | Error: {e}")
        raise

    pages_data = []
    total_text_length = 0

    for page_number, page in enumerate(doc, start=1):
        raw_text = page.get_text()
        cleaned_text = _clean_text(raw_text)

        pages_data.append({
            "page_number": page_number,
            "text": cleaned_text
        })

        total_text_length += len(cleaned_text)

    doc.close()

    if total_text_length == 0:
        logger.warning(
            f"No extractable text found in {pdf_path}. "
            "This may be a scanned/image-only PDF (OCR not supported yet)."
        )
        raise ValueError(
            "No extractable text found in this PDF. "
            "It might be a scanned document without selectable text."
        )

    logger.info(
        f"Extraction complete: {len(pages_data)} pages, "
        f"{total_text_length} characters total."
    )

    return pages_data


def _clean_text(text: str) -> str:
    """
    Basic text cleanup: remove excessive whitespace and blank lines.
    Keeps the cleaning intentionally simple for Phase 1.
    """
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines)