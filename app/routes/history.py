"""
History route.
Handles the /history endpoint: returns the saved chat history
(question/answer exchanges) for the document currently active in
the session, so the conversation can be restored after a page
refresh or when the user comes back later.
"""

from flask import Blueprint, jsonify, session
from app.services.auth_service import login_required
from app.services.chat_service import get_chat_history
from app.logger import get_logger

logger = get_logger(__name__)

history_bp = Blueprint("history", __name__)


@history_bp.route("/history", methods=["GET"])
@login_required
def get_history():
    active_document_id = session.get("active_document_id")
    active_document_name = session.get("active_document_name")

    if not active_document_id:
        return jsonify({
            "document_id": None,
            "document_name": None,
            "messages": []
        }), 200

    try:
        messages = get_chat_history(session["user_id"], active_document_id)
    except Exception as e:
        logger.error(f"Failed to load chat history: {e}")
        return jsonify({"error": "Failed to load chat history."}), 500

    return jsonify({
        "document_id": active_document_id,
        "document_name": active_document_name,
        "messages": messages
    }), 200