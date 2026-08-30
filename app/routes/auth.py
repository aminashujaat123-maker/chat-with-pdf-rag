"""
Auth routes.
Handles signup, login, and logout using Flask's built-in session
(a signed cookie storing the logged-in user's id). No extra auth
library is used, to keep dependencies minimal.
"""

from flask import Blueprint, request, jsonify, session, render_template
from app.services.auth_service import create_user, verify_user
from app.services.chat_service import get_last_active_document
from app.logger import get_logger

logger = get_logger(__name__)

auth_bp = Blueprint("auth", __name__)


# ---------------- Pages ----------------

@auth_bp.route("/signup", methods=["GET"])
def signup_page():
    return render_template("signup.html")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")


# ---------------- API ----------------

@auth_bp.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    try:
        user = create_user(username, password)
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        return jsonify({"error": "Signup failed. Please try again."}), 500

    session["user_id"] = user["id"]
    session["username"] = user["username"]

    return jsonify({
        "message": "Account created successfully.",
        "username": user["username"]
    }), 201


@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    user = verify_user(username, password)
    if user is None:
        return jsonify({"error": "Invalid username or password."}), 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]

    # Restore the last document this user was chatting with, if any,
    # so their previous conversation reappears after login.
    document_id, document_name = get_last_active_document(user["id"])
    if document_id:
        session["active_document_id"] = document_id
        session["active_document_name"] = document_name

    return jsonify({
        "message": "Logged in successfully.",
        "username": user["username"]
    }), 200


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."}), 200