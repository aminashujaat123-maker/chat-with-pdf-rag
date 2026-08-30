"""
Database module.
Sets up a lightweight SQLite database for application data such as
users (this file is stored in the database/ folder, as opposed to
the vector embeddings, which live separately in ChromaDB under
vectorstore/).
"""

import sqlite3
import os
from app.config import DATABASE_DIR
from app.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.join(DATABASE_DIR, "app.db")


def get_db_connection() -> sqlite3.Connection:
    """Open a new connection to the SQLite database.
    Row factory is set so rows can be accessed like dictionaries
    (e.g. row["username"]) instead of only by index."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all required tables if they don't already exist.
    Safe to call on every app startup."""
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            document_id TEXT NOT NULL,
            document_name TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Migration: add columns to remember each user's last active document,
    # so it can be restored after logout/login (not just within a single
    # browser session). SQLite has no "ADD COLUMN IF NOT EXISTS", so we
    # try to add it and ignore the error if it already exists.
    for column_def in [
        "ALTER TABLE users ADD COLUMN last_document_id TEXT",
        "ALTER TABLE users ADD COLUMN last_document_name TEXT",
    ]:
        try:
            conn.execute(column_def)
        except sqlite3.OperationalError:
            pass  # column already exists, nothing to do

    conn.commit()
    conn.close()
    logger.info(f"Database initialized at: {DB_PATH}")