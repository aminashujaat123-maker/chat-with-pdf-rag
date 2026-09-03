"""
Generator module.
Takes the user's question and the chunks retrieved from the vector
store, builds a prompt that instructs the LLM to answer only from
the given context, and calls Groq's API to generate the final
natural-language answer.

This is the "Generation" step in RAG: turning retrieved raw chunks
into a coherent, grounded answer for the user.
"""

from groq import Groq
from app.config import LLM_API_KEY, LLM_MODEL_NAME, LLM_TEMPERATURE
from app.logger import get_logger

logger = get_logger(__name__)

# Module-level cache so the Groq client is created only once per
# process, not once per request.
_client_cache = None

SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions using ONLY the "
    "context provided below, which was extracted from a PDF document. "
    "Follow these rules strictly:\n"
    "1. Only use information found in the provided context to answer.\n"
    "2. If the answer is not found in the context, say clearly that you "
    "could not find the answer in the document. Do not guess or use "
    "outside knowledge.\n"
    "3. Keep your answer clear and directly relevant to the question."
)

SUMMARY_SYSTEM_PROMPT = (
    "You are a helpful assistant that writes clear summaries of documents. "
    "You will be given the full text content of a PDF document, extracted "
    "page by page. Write a well-organized summary that:\n"
    "1. Gives a brief overview of what the document is about.\n"
    "2. Lists the key topics or sections covered.\n"
    "3. Highlights any particularly important points, definitions, or "
    "conclusions.\n"
    "Base the summary only on the provided content — do not add outside "
    "knowledge or make assumptions beyond what is written."
)

# Whole-document summaries can involve a lot of text. This caps how much
# context is sent to the LLM to stay within a safe token budget; if the
# document is longer, only the earliest pages (up to this limit) are used.
MAX_SUMMARY_CONTEXT_CHARS = 15000
QUICK_ACTION_PROMPTS = {
    "explain": (
        "You are a helpful tutor. You will be given the full text content of a "
        "PDF document, extracted page by page. Explain what this document is "
        "about in simple, beginner-friendly language, as if teaching someone "
        "new to the topic. Avoid jargon where possible, and explain any "
        "necessary technical terms in plain words. Base your explanation only "
        "on the provided content."
    ),
    "key_points": (
        "You are a helpful assistant that extracts key points from documents. "
        "You will be given the full text content of a PDF document, extracted "
        "page by page. List the most important points, facts, and ideas from "
        "the document as a clear bulleted list. Base this only on the provided "
        "content — do not add outside knowledge."
    ),
    "questions": (
        "You are a helpful assistant that creates study questions from "
        "documents. You will be given the full text content of a PDF "
        "document, extracted page by page. Generate 5-8 thoughtful questions "
        "(a mix of factual and conceptual) that a student could use to test "
        "their understanding of this material. Number the questions. Base "
        "them only on the provided content."
    ),
}

QUICK_ACTION_LABELS = {
    "explain": "Explain this document simply",
    "key_points": "Give me the key points",
    "questions": "Generate study questions",
}


def _get_client() -> Groq:
    """Create (on first use) and reuse the Groq API client."""
    global _client_cache

    if _client_cache is None:
        if not LLM_API_KEY:
            raise ValueError(
                "LLM_API_KEY is not set. Please add your Groq API key "
                "to the .env file."
            )
        _client_cache = Groq(api_key=LLM_API_KEY)

    return _client_cache


def _build_context(chunks: list[dict]) -> str:
    """
    Combine chunks into a single context string, labeling each piece
    with its page number so the model's answer can be traced back to
    a specific page.
    """
    context_parts = []
    for chunk in chunks:
        page = chunk.get("page_number", "unknown")
        text = chunk.get("text", "")
        context_parts.append(f"[Page {page}]\n{text}")

    return "\n\n---\n\n".join(context_parts)


def generate_answer(question: str, chunks: list[dict]) -> str:
    """
    Generate a final natural-language answer to the user's question,
    grounded in the given retrieved chunks (the top-k chunks most
    relevant to this specific question).
    """
    client = _get_client()
    context = _build_context(chunks)

    user_prompt = (
        f"Context from the document:\n\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer the question using only the context above."
    )

    logger.info(f"Sending question to LLM (model={LLM_MODEL_NAME}) ...")

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        temperature=LLM_TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )

    answer = response.choices[0].message.content

    logger.info("LLM answer generated successfully.")

    return answer


def generate_summary(chunks: list[dict]) -> str:
    """
    Generate a whole-document summary from ALL of a document's chunks
    (not just the top-k relevant to a specific question). This avoids
    the problem of semantic retrieval missing most of the document
    when there's no specific query to match against — a "summarize
    this" request needs the full content, not just similar-sounding
    pieces.

    Args:
        chunks: Every chunk belonging to the document, ordered by
                page number (output of get_all_chunks_for_document()).

    Returns:
        The LLM's generated summary as a plain string.
    """
    client = _get_client()
    context = _build_context(chunks)

    truncated = False
    if len(context) > MAX_SUMMARY_CONTEXT_CHARS:
        context = context[:MAX_SUMMARY_CONTEXT_CHARS]
        truncated = True

    user_prompt = f"Full document content:\n\n{context}\n\nWrite a summary of this document."

    if truncated:
        user_prompt += (
            "\n\n(Note: this document is long, so only its earlier "
            "portion is shown above. Summarize based on what is available.)"
        )

    logger.info(
        f"Generating whole-document summary (model={LLM_MODEL_NAME}, "
        f"context_chars={len(context)}, truncated={truncated}) ..."
    )

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        temperature=LLM_TEMPERATURE,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
    )

    summary = response.choices[0].message.content

    logger.info("Summary generated successfully.")

    return summary
def generate_quick_action(action: str, chunks: list[dict]) -> str:
    """
    Generate a document-wide response for a preset quick action
    (Explain, Key Points, Generate Questions), using ALL of the
    document's chunks — same reasoning as generate_summary(): these
    requests are about the whole document, not a specific question
    that semantic retrieval could target.
    """
    if action not in QUICK_ACTION_PROMPTS:
        raise ValueError(f"Unknown quick action: {action}")

    client = _get_client()
    context = _build_context(chunks)

    truncated = False
    if len(context) > MAX_SUMMARY_CONTEXT_CHARS:
        context = context[:MAX_SUMMARY_CONTEXT_CHARS]
        truncated = True

    user_prompt = f"Full document content:\n\n{context}\n\nPlease respond according to your instructions."

    if truncated:
        user_prompt += (
            "\n\n(Note: this document is long, so only its earlier "
            "portion is shown above. Base your response on what is available.)"
        )

    logger.info(f"Generating quick action '{action}' (model={LLM_MODEL_NAME}) ...")

    response = client.chat.completions.create(
        model=LLM_MODEL_NAME,
        temperature=LLM_TEMPERATURE,
        messages=[
            {"role": "system", "content": QUICK_ACTION_PROMPTS[action]},
            {"role": "user", "content": user_prompt}
        ]
    )

    result = response.choices[0].message.content

    logger.info(f"Quick action '{action}' generated successfully.")

    return result