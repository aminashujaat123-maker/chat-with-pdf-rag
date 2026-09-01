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
    """Add a list of embedded chunks to the vector store."""
    if not chunks:
        return 0

    collection = _get_collection()

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
    """Return the total number of chunks currently stored across all documents."""
    collection = _get_collection()
    return collection.count()


def query_similar_chunks(query_embedding: list[float], top_k: int, document_id: str = None) -> list[dict]:
    """Find the chunks most semantically similar to a given query embedding."""
    collection = _get_collection()

    where_filter = {"document_id": document_id} if document_id else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
    )

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


def search_chunks_by_keyword(query_text: str, document_id: str) -> list[dict]:
    """Find all chunks belonging to a document that contain a literal
    (case-insensitive) match of the given search term."""
    collection = _get_collection()

    results = collection.get(where={"document_id": document_id})

    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    query_lower = query_text.lower()
    matches = []

    for text, metadata in zip(documents, metadatas):
        if query_lower in text.lower():
            matches.append({
                "text": text,
                "page_number": metadata.get("page_number"),
                "chunk_id": metadata.get("chunk_id")
            })

    matches.sort(key=lambda m: m["page_number"])

    return matches


def get_all_chunks_for_document(document_id: str) -> list[dict]:
    """
    Fetch every chunk belonging to a document, ordered by page number.
    Unlike query_similar_chunks() (which returns only the top-k chunks
    most relevant to a specific question), this returns the ENTIRE
    document's content — needed for whole-document summarization,
    where there's no single query to semantically match against.
    """
    collection = _get_collection()

    results = collection.get(where={"document_id": document_id})

    documents = results.get("documents", [])
    metadatas = results.get("metadatas", [])

    chunks = [
        {
            "text": text,
            "page_number": metadata.get("page_number", 0),
            "chunk_id": metadata.get("chunk_id", 0)
        }
        for text, metadata in zip(documents, metadatas)
    ]

    chunks.sort(key=lambda c: (c["page_number"], c["chunk_id"]))

    return chunks
def get_document_owner_and_name(document_id: str) -> tuple[int, str] | tuple[None, None]:
    """
    Look up which user owns a document and its display name, by
    reading the metadata off any one of its stored chunks. Used to
    verify ownership before allowing a delete.
    """
    collection = _get_collection()
    results = collection.get(where={"document_id": document_id}, limit=1)

    metadatas = results.get("metadatas", [])
    if not metadatas:
        return None, None

    metadata = metadatas[0]
    return metadata.get("user_id"), metadata.get("document_name")


def delete_document_chunks(document_id: str) -> None:
    """Delete every chunk belonging to a document from the vector store."""
    collection = _get_collection()
    collection.delete(where={"document_id": document_id})
    logger.info(f"Deleted all chunks for document_id={document_id} from vector store.")