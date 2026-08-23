"""
Text splitter module.
Breaks the extracted page text into smaller overlapping chunks.
This is a core RAG step: instead of sending the entire document to
the LLM, we split it into chunks so only the most relevant pieces
are retrieved and sent as context later.

Chunking is done per page (not across the whole document) so that
each chunk keeps an accurate page number, which is needed for
source citations.
"""

from app.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.logger import get_logger

logger = get_logger(__name__)


def chunk_pages(pages_data: list[dict]) -> list[dict]:
    """
    Split extracted page text into overlapping chunks.

    Args:
        pages_data: Output of extract_text_from_pdf(), in the form:
            [{"page_number": 1, "text": "..."}, ...]

    Returns:
        A list of chunk dicts, in the form:
        [
            {
                "chunk_id": 0,
                "page_number": 1,
                "text": "...",
                "char_count": 780
            },
            ...
        ]
    """
    all_chunks = []
    chunk_id = 0

    for page in pages_data:
        page_number = page["page_number"]
        page_text = page["text"]

        page_chunks = _split_text(page_text, CHUNK_SIZE, CHUNK_OVERLAP)

        for chunk_text in page_chunks:
            all_chunks.append({
                "chunk_id": chunk_id,
                "page_number": page_number,
                "text": chunk_text,
                "char_count": len(chunk_text)
            })
            chunk_id += 1

    logger.info(
        f"Chunking complete: {len(pages_data)} pages -> {len(all_chunks)} chunks "
        f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})."
    )

    return all_chunks


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Split a single string into overlapping chunks using a sliding window
    over characters. Tries to break at the nearest space so words are
    not cut in half, whenever possible.

    Args:
        text: The text to split.
        chunk_size: Target maximum length of each chunk, in characters.
        chunk_overlap: How many characters should overlap between
                       consecutive chunks (helps preserve context
                       across chunk boundaries).

    Returns:
        A list of text chunks. Returns an empty list if the input
        text is empty.
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        if end >= text_length:
            # Last chunk: take whatever is left
            chunks.append(text[start:text_length].strip())
            break

        # Try to break at the nearest space before 'end' to avoid
        # cutting a word in half.
        break_point = text.rfind(" ", start, end)
        if break_point == -1 or break_point <= start:
            # No space found, force break at 'end'
            break_point = end

        chunks.append(text[start:break_point].strip())

        # Move the window forward, stepping back by chunk_overlap
        # so consecutive chunks share some context.
        start = break_point - chunk_overlap
        if start < 0:
            start = break_point

    # Remove any empty chunks that may have resulted from stripping
    return [chunk for chunk in chunks if chunk]