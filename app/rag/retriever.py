"""
Retriever module.
Given a user's question, this module:
  1. Converts the question into an embedding (same model as the chunks).
  2. Searches the vector store for the most semantically similar chunks.

This is the core of "Retrieval" in RAG: finding the pieces of the
document(s) that are most likely to contain the answer, so only
those (not the whole document) get sent to the LLM later.
"""

from app.rag.embedder import embed_query
from app.rag.vectorstore import query_similar_chunks
from app.config import TOP_K
from app.logger import get_logger

logger = get_logger(__name__)


def retrieve_relevant_chunks(question: str, top_k: int = TOP_K) -> list[dict]:
    """
    Find the chunks most relevant to a user's question.

    Args:
        question: The user's natural-language question.
        top_k: How many relevant chunks to retrieve (defaults to
               the TOP_K value set in config.py).

    Returns:
        A list of chunk result dicts (see query_similar_chunks()
        in vectorstore.py for the exact shape), ordered from most
        to least relevant.
    """
    logger.info(f"Retrieving top {top_k} chunks for question: '{question}'")

    query_embedding = embed_query(question)
    results = query_similar_chunks(query_embedding, top_k)

    logger.info(f"Retrieved {len(results)} chunks.")

    return results