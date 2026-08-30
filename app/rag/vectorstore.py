"""
Vector store module.
Wraps ChromaDB to store and retrieve chunk embeddings on disk, so
they persist across requests and app restarts (unlike the in-memory
data from the chunking/embedding steps, which disappears once a
request finishes).

For Phase 1 (MVP), all chunks from all uploaded PDFs are stored in
a single ChromaDB collection. Each chunk's metadata includes the
document ID and page number, so chunks can later be filtered back
to a specific document and cited by page.
"""

import chromadb
from chromadb.config import Settings
from app.config import VECTORSTORE_DIR
from app.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "pdf_chunks"

# Module-level cache so the ChromaDB client/collection is created
# only once per process, not once per function call.
_client_cache = None
_collection_cache = None


def _get_collection():
    """Get (or create, on first use) the ChromaDB collection used
    to store all PDF chunks."""
    global _client_cache, _collection_cache

    if _collection_cache is None:
        logger.info(f"Initializing ChromaDB at: {VECTORSTORE_DIR}")
        _client_cache = chromadb.PersistentClient(
            path=VECTORSTORE_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        _collection_cache = _client_cache.get_or_create_collection(
            name=COLLECTION_NAME
        )
        logger.info(f"ChromaDB collection '{COLLECTION_NAME}' ready.")

    return _collection_cache


def add_chunks_to_store(chunks: list[dict], document_id: str, document_name: str, user_id: int = None) -> int:
    """
    Add a list of embedded chunks to the vector store.

    Args:
        chunks: Output of embed_chunks(), where each chunk dict has
                "chunk_id", "page_number", "text", and "embedding".
        document_id: A unique identifier for the source document
                     (we use the stored_filename from file_service,
                     since it is already unique per upload).
        document_name: The original filename, stored as metadata so
                       it can be shown to the user later (e.g. in
                       source citations).
        user_id: The id of the user who uploaded this document, so
                 documents can later be scoped/filtered per user.

    Returns:
        The number of chunks added to the store.
    """
    if not chunks:
        return 0

    collection = _get_collection()

    # ChromaDB needs a separate, globally unique ID for every entry.
    # We combine the document_id and chunk_id so chunks from
    # different documents never collide.
    ids = [f"{document_id}_chunk_{chunk['chunk_id']}" for chunk in chunks]
    embeddings = [chunk["embedding"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [
        {
            "document_id": document_id,
            "document_name": document_name,
            "page_number": chunk["page_number"],
            "chunk_id": chunk["chunk_id"],
            "user_id": user_id if user_id is not None else -1,
        }
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    logger.info(
        f"Stored {len(chunks)} chunks in vector store for document "
        f"'{document_name}' (document_id={document_id})."
    )

    return len(chunks)


def get_total_chunk_count() -> int:
    """Return the total number of chunks currently stored across all documents.
    Useful for quick sanity checks and for the analytics dashboard later."""
    collection = _get_collection()
    return collection.count()


def query_similar_chunks(query_embedding: list[float], top_k: int, document_id: str = None) -> list[dict]:
    """
    Find the chunks most semantically similar to a given query embedding.

    Args:
        query_embedding: The embedding vector of the user's question.
        top_k: How many of the most similar chunks to return.
        document_id: If provided, restricts the search to chunks
                     belonging only to this document. This is what
                     keeps answers scoped to the document currently
                     being chatted with, instead of searching across
                     every document ever uploaded.

    Returns:
        A list of chunk result dicts, ordered from most to least
        similar, in the form:
        [
            {
                "text": "...",
                "document_id": "...",
                "document_name": "...",
                "page_number": 3,
                "distance": 0.42
            },
            ...
        ]
        Note: "distance" is a similarity distance (lower = more similar),
        not a percentage score.
    """
    collection = _get_collection()

    where_filter = {"document_id": document_id} if document_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
    )

    # ChromaDB returns results wrapped in an extra outer list
    # (one entry per query embedding); we only sent one query,
    # so we unwrap that single entry here.
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    chunk_results = []
    for text, metadata, distance in zip(documents, metadatas, distances):
        chunk_results.append({
            "text": text,
            "document_id": metadata.get("document_id"),
            "document_name": metadata.get("document_name"),
            "page_number": metadata.get("page_number"),
            "distance": distance
        })

    return chunk_results