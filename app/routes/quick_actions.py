"""
Quick actions route.
Handles the /quick-action endpoint: generates document-wide responses
for preset actions (Explain, Key Points, Generate Questions) using
ALL of the active document's chunks — similar to /summarize, since
these requests are about the whole document rather than a specific
question that semantic retrieval could target.
"""

from flask import Blueprint, request, jsonify, session
from app.rag.vectorstore import get_all_chunks_for_document
from app.rag.generator import generate_quick_action, QUICK_ACTION_LABELS
from app.services.auth_service import login_required
from app.services.chat_service import save_message
from app.logger import get_logger

logger = get_logger(__name__)

quick_actions_bp = Blueprint("quick_actions", __name__)


@quick_actions_bp.route("/quick-action", methods=["POST"])
@login_required
def run_quick_action():
    data = request.get_json(silent=True) or {}
    action = data.get("action")

    if action not in QUICK_ACTION_LABELS:
        return jsonify({"error": "Invalid action."}), 400

    active_document_id = session.get("active_document_id")
    active_document_name = session.get("active_document_name")

    if not active_document_id:
        return jsonify({"error": "Please upload a PDF first."}), 400

    try:
        chunks = get_all_chunks_for_document(active_document_id)
    except Exception as e:
        logger.error(f"Failed to fetch chunks for quick action: {e}")
        return jsonify({"error": "Failed to load the document."}), 500

    if not chunks:
        return jsonify({"error": "No content found for this document."}), 404

    try:
        result = generate_quick_action(action, chunks)
    except Exception as e:
        logger.error(f"Quick action '{action}' failed: {e}")
        return jsonify({"error": "Failed to generate a response."}), 500

    question_label = QUICK_ACTION_LABELS[action]
    sources = [{"document_name": active_document_name, "page_number": "all"}]

    try:
        save_message(
            user_id=session["user_id"],
            document_id=active_document_id,
            document_name=active_document_name,
            question=question_label,
            answer=result,
            sources=sources
        )
    except Exception as e:
        logger.error(f"Failed to save quick action to chat history: {e}")

    return jsonify({
        "question": question_label,
        "answer": result,
        "sources": sources
    }), 200