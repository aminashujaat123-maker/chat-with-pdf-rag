"""
Health-check endpoint. This simply confirms the server is running —
no RAG logic is involved here. Useful during deployment/debugging
to check whether the app is alive or not.
"""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "message": "Chat-with-PDF RAG server is running."
    }), 200