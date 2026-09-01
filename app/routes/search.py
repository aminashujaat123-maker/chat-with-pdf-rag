"""
Search route.
Handles the /search endpoint: performs a literal keyword search
across the chunks of the currently active document, returning the
pages and snippets where the term appears.

This is different from /ask — /ask generates an LLM answer from
semantically relevant chunks, while /search simply finds exact
occurrences of a word or phrase, similar to Ctrl+F within the
document. No LLM call is made, so it's fast and free.
"""

from flask import Blueprint, request, jsonify, session
from app.rag.vectorstore import search_chunks_by_keyword
from app.services.auth_service import login_required
from app.logger import get_logger

logger = get_logger(__name__)

search_bp = Blueprint("search", __name__)


@search_bp.route("/search", methods=["GET"])
@login_required
def search_document():
    query = (request.args.get("q") or "").strip()

    if not query:
        return jsonify({"error": "A search query ('q') is required."}), 400

    active_document_id = session.get("active_document_id")

    if not active_document_id:
        return jsonify({
            "query": query,
            "results": [],
            "message": "Upload a PDF before searching."
        }), 200

    try:
        matches = search_chunks_by_keyword(query, active_document_id)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return jsonify({"error": "Search failed."}), 500

    # Cap the number of results returned to keep the UI manageable
    MAX_RESULTS = 10

    return jsonify({
        "query": query,
        "results_count": len(matches),
        "results": matches[:MAX_RESULTS]
    }), 200