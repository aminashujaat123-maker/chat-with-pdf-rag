"""
Documents route.
Handles listing all documents a user has ever chatted with (for the
sidebar history list, similar to ChatGPT/Claude's conversation list),
and switching the "active" document for the current session so a
past conversation can be resumed.
"""

from flask import Blueprint, request, jsonify, session
from app.services.auth_service import login_required
from app.services.chat_service import (
    get_user_documents,
    get_document_name_for_user,
    set_last_active_document
)
from app.logger import get_logger

logger = get_logger(__name__)

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/documents", methods=["GET"])
@login_required
def list_documents():
    try:
        documents = get_user_documents(session["user_id"])
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        return jsonify({"error": "Failed to load document history."}), 500

    return jsonify({
        "documents": documents,
        "active_document_id": session.get("active_document_id")
    }), 200


@documents_bp.route("/documents/select", methods=["POST"])
@login_required
def select_document():
    data = request.get_json(silent=True) or {}
    document_id = data.get("document_id")

    if not document_id:
        return jsonify({"error": "document_id is required."}), 400

    # Verify this document actually belongs to the current user
    # before switching to it (prevents guessing other users' document ids).
    document_name = get_document_name_for_user(session["user_id"], document_id)

    if document_name is None:
        return jsonify({"error": "Document not found."}), 404

    session["active_document_id"] = document_id
    session["active_document_name"] = document_name

    try:
        set_last_active_document(session["user_id"], document_id, document_name)
    except Exception as e:
        logger.error(f"Failed to persist active document on switch: {e}")

    return jsonify({
        "document_id": document_id,
        "document_name": document_name
    }), 200