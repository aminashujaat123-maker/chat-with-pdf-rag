"""
Auth service.
Handles user creation and credential verification against the SQLite
users table. Passwords are never stored in plain text — only a
salted hash (via Werkzeug's built-in security helpers) is stored.

Also provides decorators to protect routes that require a logged-in
user: one for JSON API routes (returns a 401 error) and one for
HTML page routes (redirects to the login page).
"""

from functools import wraps
from flask import session, jsonify, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import get_db_connection
from app.logger import get_logger

logger = get_logger(__name__)


def create_user(username: str, password: str) -> dict:
    """
    Create a new user with a hashed password.

    Raises:
        ValueError: If the username is already taken.

    Returns:
        A dict with the new user's id and username.
    """
    conn = get_db_connection()

    existing = conn.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()

    if existing:
        conn.close()
        raise ValueError("Username is already taken.")

    password_hash = generate_password_hash(password)
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    logger.info(f"New user created: '{username}' (id={user_id})")

    return {"id": user_id, "username": username}


def verify_user(username: str, password: str) -> dict | None:
    """
    Check a username/password pair against the database.

    Returns:
        A dict with the user's id and username if the credentials
        are valid, otherwise None.
    """
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    if not check_password_hash(row["password_hash"], password):
        return None

    return {"id": row["id"], "username": row["username"]}


def login_required(view_func):
    """
    Decorator for JSON API routes. If no user is logged in, returns
    a 401 JSON error instead of calling the wrapped view.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return view_func(*args, **kwargs)
    return wrapped


def login_required_page(view_func):
    """
    Decorator for HTML page routes. If no user is logged in,
    redirects to the login page instead of rendering the view.
    """
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login_page"))
        return view_func(*args, **kwargs)
    return wrapped