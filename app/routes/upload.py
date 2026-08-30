"""
Upload route.
Handles the /upload endpoint: receives a PDF file, validates it,
saves it to disk, and extracts its text using the RAG loader.

Note: In this step (Phase 1, Step 2), we only extract and return text.
Chunking, embeddings, and vector storage will be added in later steps.
"""

from flask import Blueprint, request, jsonify, session
from app.services.file_service import (
    is_allowed_file,
    is_within_size_limit,
    save_uploaded_file
)
from app.rag.loader import extract_text_from_pdf
from app.rag.splitter import chunk_pages
from app.rag.embedder import embed_chunks
from app.rag.vectorstore import add_chunks_to_store
from app.services.auth_service import login_required
from app.services.chat_service import set_last_active_document
from app.config import MAX_FILE_SIZE_MB
from app.logger import get_logger

logger = get_logger(__name__)

upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/upload", methods=["POST"])
@login_required
def upload_pdf():
    # 1. Check if a file was sent at all
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    # 2. Validate file extension
    if not is_allowed_file(uploaded_file.filename):
        return jsonify({
            "error": "Invalid file type. Only .pdf files are allowed."
        }), 400

    # 3. Validate file size
    if not is_within_size_limit(uploaded_file.stream):
        return jsonify({
            "error": f"File is too large. Maximum allowed size is {MAX_FILE_SIZE_MB} MB."
        }), 400

    # 4. Save the file to disk
    try:
        file_metadata = save_uploaded_file(uploaded_file)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        return jsonify({"error": "Failed to save the uploaded file."}), 500

    # 5. Extract text from the saved PDF
    try:
        pages_data = extract_text_from_pdf(file_metadata["file_path"])
    except ValueError as e:
        # Raised when the PDF has no extractable text (e.g. scanned PDF)
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return jsonify({"error": "Failed to process the PDF file."}), 500

    # 6. Split the extracted text into overlapping chunks
    #    (chunking makes it possible to later retrieve only the most
    #    relevant pieces of the document instead of the whole thing)
    chunks = chunk_pages(pages_data)

    # 7. Generate an embedding vector for each chunk
    #    (embeddings allow semantic search later on, once they are
    #    stored in the vector database in the next step)
    try:
        chunks = embed_chunks(chunks)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        return jsonify({"error": "Failed to generate embeddings for the document."}), 500

    # 8. Store the embedded chunks in the vector database (ChromaDB)
    #    so they persist across requests and can be searched later.
    #    The stored_filename is used as the document_id since it is
    #    already guaranteed to be unique per upload.
    try:
        stored_count = add_chunks_to_store(
            chunks=chunks,
            document_id=file_metadata["stored_filename"],
            document_name=file_metadata["original_filename"],
            user_id=session.get("user_id")
        )
    except Exception as e:
        logger.error(f"Failed to store chunks in vector database: {e}")
        return jsonify({"error": "Failed to store the document in the vector database."}), 500

    # 8b. Mark this document as the "active" one for the current session,
    #     so that /ask only searches within it instead of across every
    #     document ever uploaded (by anyone). Also persist it to the
    #     database so it survives a logout/login (not just this session).
    session["active_document_id"] = file_metadata["stored_filename"]
    session["active_document_name"] = file_metadata["original_filename"]

    try:
        set_last_active_document(
            user_id=session["user_id"],
            document_id=file_metadata["stored_filename"],
            document_name=file_metadata["original_filename"]
        )
    except Exception as e:
        logger.error(f"Failed to persist active document: {e}")

    # 9. Return a success response with basic info
    #    (full page/chunk text and embeddings are omitted from the
    #    response to keep it light; only previews are included for now)
    return jsonify({
        "message": "PDF uploaded and processed successfully.",
        "file": {
            "original_filename": file_metadata["original_filename"],
            "stored_filename": file_metadata["stored_filename"],
            "size_mb": file_metadata["size_mb"]
        },
        "pages_count": len(pages_data),
        "chunks_count": len(chunks),
        "stored_chunks_count": stored_count,
        "embedding_dimension": len(chunks[0]["embedding"]) if chunks else 0,
        "first_page_preview": pages_data[0]["text"][:300] if pages_data else "",
        "first_chunk_preview": chunks[0]["text"][:300] if chunks else ""
    }), 200