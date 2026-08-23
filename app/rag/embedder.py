"""
Embedder module.
Converts text chunks into numerical vectors (embeddings) using a
local Sentence Transformers model. These embeddings capture semantic
meaning, which allows the vector database to later find chunks that
are conceptually similar to a user's question, not just keyword matches.

The model is loaded once and reused across requests, since loading
it from disk/downloading it is relatively expensive and should not
happen on every single upload or query.
"""

from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL_NAME
from app.logger import get_logger

logger = get_logger(__name__)

# Module-level cache so the model is loaded only once per process,
# not once per function call.
_model_cache = None


def _get_model() -> SentenceTransformer:
    """Load the embedding model on first use, then reuse it afterwards."""
    global _model_cache

    if _model_cache is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME} ...")
        _model_cache = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("Embedding model loaded successfully.")

    return _model_cache


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Generate an embedding vector for each chunk's text.

    Args:
        chunks: Output of chunk_pages(), in the form:
            [{"chunk_id": 0, "page_number": 1, "text": "...", ...}, ...]

    Returns:
        The same list of chunk dicts, with an added "embedding" key
        for each chunk, containing a list of floats:
        [
            {
                "chunk_id": 0,
                "page_number": 1,
                "text": "...",
                "char_count": 780,
                "embedding": [0.021, -0.153, 0.782, ...]
            },
            ...
        ]
    """
    if not chunks:
        return []

    model = _get_model()

    texts = [chunk["text"] for chunk in chunks]

    logger.info(f"Generating embeddings for {len(texts)} chunks ...")
    vectors = model.encode(texts, show_progress_bar=False)
    logger.info("Embedding generation complete.")

    for chunk, vector in zip(chunks, vectors):
        chunk["embedding"] = vector.tolist()

    return chunks


def embed_query(query_text: str) -> list[float]:
    """
    Generate an embedding vector for a single piece of text
    (used later for embedding the user's question before
    searching the vector database).

    Args:
        query_text: The text to embed (e.g. a user's question).

    Returns:
        A list of floats representing the embedding vector.
    """
    model = _get_model()
    vector = model.encode(query_text, show_progress_bar=False)
    return vector.tolist()