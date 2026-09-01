"""
Summarize route.
Handles the /summarize endpoint: generates a whole-document summary
for the currently active document by sending ALL of its chunks to
the LLM (unlike /ask, which only sends the top few chunks relevant
to a specific question). This gives much better summaries, since a
"give me a summary" request doesn't correspond to any single piece
of content that semantic retrieval could reliably find.
"""

from flask import Blueprint, jsonify, session
from app.rag.vectorstore import get_all_chunks_for_document
from app.rag.generator import generate_summary
from app.services.auth_service import login_required
from app.services.chat_service import save_message
from app.logger import get_logger

logger = get_logger(__name__)

summarize_bp = Blueprint("summarize", __name__)


@summarize_bp.route("/summarize", methods=["POST"])
@login_required
def summarize_document():
    active_document_id = session.get("active_document_id")
    active_document_name = session.get("active_document_name")

    if not active_document_id:
        return jsonify({"error": "Please upload a PDF before requesting a summary."}), 400

    try:
        chunks = get_all_chunks_for_document(active_document_id)
    except Exception as e:
        logger.error(f"Failed to fetch chunks for summary: {e}")
        return jsonify({"error": "Failed to load the document for summarization."}), 500

    if not chunks:
        return jsonify({"error": "No content found for this document."}), 404

    try:
        summary = generate_summary(chunks)
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        return jsonify({"error": "Failed to generate a summary."}), 500

    question_label = "Summarize this document"
    sources = [{"document_name": active_document_name, "page_number": "all"}]

    # Save this as a regular chat exchange too, so it shows up
    # naturally in the conversation history like any other Q&A.
    try:
        save_message(
            user_id=session["user_id"],
            document_id=active_document_id,
            document_name=active_document_name,
            question=question_label,
            answer=summary,
            sources=sources
        )
    except Exception as e:
        logger.error(f"Failed to save summary to chat history: {e}")

    return jsonify({
        "question": question_label,
        "answer": summary,
        "sources": sources
    }), 200