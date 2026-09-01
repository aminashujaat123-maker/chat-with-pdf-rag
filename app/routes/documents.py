"""
Documents route.
Handles listing all documents a user has ever chatted with (for the
sidebar history list), switching the "active" document for the
current session, and deleting documents entirely (chunks, chat
history, and the uploaded file on disk).
"""

import os
from flask import Blueprint, request, jsonify, session
from app.services.auth_service import login_required
from app.services.chat_service import (
    get_user_documents,
    get_document_name_for_user,
    set_last_active_document,
    delete_document_messages,
    clear_last_active_document_if_matches
)
from app.rag.vectorstore import (
    get_document_owner_and_name,
    delete_document_chunks
)
from app.config import UPLOAD_FOLDER
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


@documents_bp.route("/documents/<document_id>", methods=["DELETE"])
@login_required
def delete_document(document_id):
    # Verify ownership using the vector store's chunk metadata
    # (works even if the document has no chat messages yet).
    owner_id, document_name = get_document_owner_and_name(document_id)

    if owner_id is None or owner_id != session["user_id"]:
        return jsonify({"error": "Document not found."}), 404

    # 1. Remove chunks from the vector store
    try:
        delete_document_chunks(document_id)
    except Exception as e:
        logger.error(f"Failed to delete chunks for {document_id}: {e}")
        return jsonify({"error": "Failed to delete the document."}), 500

    # 2. Remove chat history for this document
    try:
        delete_document_messages(session["user_id"], document_id)
    except Exception as e:
        logger.error(f"Failed to delete chat history for {document_id}: {e}")

    # 3. Clear it as the "last active document" if it was
    try:
        clear_last_active_document_if_matches(session["user_id"], document_id)
    except Exception as e:
        logger.error(f"Failed to clear last active document: {e}")

    # 4. Delete the actual PDF file from disk
    #    (document_id is the stored_filename, so this reconstructs the path)
    file_path = os.path.join(UPLOAD_FOLDER, document_id)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {e}")

    # 5. If this was the active document in the current session, clear it
    if session.get("active_document_id") == document_id:
        session.pop("active_document_id", None)
        session.pop("active_document_name", None)

    logger.info(f"Deleted document '{document_name}' (document_id={document_id})")

    return jsonify({"message": f"Deleted {document_name}."}), 200