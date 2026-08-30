"""
Chat service.
Handles saving each question/answer exchange to the SQLite database,
and retrieving the chat history for a given user and document so it
can be restored (e.g. after a page refresh).
"""

import json
from app.db import get_db_connection
from app.logger import get_logger

logger = get_logger(__name__)


def save_message(user_id: int, document_id: str, document_name: str,
                  question: str, answer: str, sources: list) -> None:
    """
    Save a single question/answer exchange to the database.
    """
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO messages (user_id, document_id, document_name, question, answer, sources)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, document_id, document_name, question, answer, json.dumps(sources))
    )
    conn.commit()
    conn.close()

    logger.info(f"Saved chat message for user_id={user_id}, document_id={document_id}")


def get_chat_history(user_id: int, document_id: str) -> list[dict]:
    """
    Retrieve the full chat history for a user and a specific document,
    ordered from oldest to newest.
    """
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT question, answer, sources FROM messages
        WHERE user_id = ? AND document_id = ?
        ORDER BY created_at ASC
        """,
        (user_id, document_id)
    ).fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "question": row["question"],
            "answer": row["answer"],
            "sources": json.loads(row["sources"]) if row["sources"] else []
        })

    return history


def set_last_active_document(user_id: int, document_id: str, document_name: str) -> None:
    """
    Remember which document a user was last chatting with, persisted
    in the database (not just the session), so it can be restored
    even after the user logs out and logs back in.
    """
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET last_document_id = ?, last_document_name = ? WHERE id = ?",
        (document_id, document_name, user_id)
    )
    conn.commit()
    conn.close()


def get_last_active_document(user_id: int) -> tuple[str, str] | tuple[None, None]:
    """
    Retrieve the document a user was last chatting with.
    """
    conn = get_db_connection()
    row = conn.execute(
        "SELECT last_document_id, last_document_name FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None, None

    return row["last_document_id"], row["last_document_name"]


def get_user_documents(user_id: int) -> list[dict]:
    """
    Get a list of all documents a user has ever chatted with, most
    recently active first. Used to populate the sidebar chat history
    list (similar to ChatGPT/Claude's conversation list).
    """
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT document_id, document_name, MAX(created_at) AS last_active_at
        FROM messages
        WHERE user_id = ?
        GROUP BY document_id
        ORDER BY last_active_at DESC
        """,
        (user_id,)
    ).fetchall()
    conn.close()

    return [
        {
            "document_id": row["document_id"],
            "document_name": row["document_name"],
            "last_active_at": row["last_active_at"]
        }
        for row in rows
    ]


def get_document_name_for_user(user_id: int, document_id: str) -> str | None:
    """
    Look up a document's name, but only if it belongs to (i.e. has
    chat messages from) the given user. Used to validate ownership
    when a user tries to switch to a document by id.
    """
    conn = get_db_connection()
    row = conn.execute(
        "SELECT document_name FROM messages WHERE user_id = ? AND document_id = ? LIMIT 1",
        (user_id, document_id)
    ).fetchone()
    conn.close()

    return row["document_name"] if row else None