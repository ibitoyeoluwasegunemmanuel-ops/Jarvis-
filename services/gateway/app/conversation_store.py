"""Private, owner-scoped persistence for the local JARVIS conversation."""

from __future__ import annotations

import time
from typing import Any

from app.owner_auth import connect_database

MAX_HISTORY_MESSAGES = 100


def _ensure_table(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL DEFAULT 1 REFERENCES owner_account(id),
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 8000),
            created_at REAL NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS conversation_messages_owner_created
        ON conversation_messages(owner_id, created_at DESC, id DESC)
        """
    )


def list_conversation_history(limit: int = 40) -> list[dict[str, Any]]:
    """Return the most recent conversation messages in chronological order."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_HISTORY_MESSAGES:
        raise ValueError("conversation_history_limit_invalid")
    connection = connect_database()
    try:
        _ensure_table(connection)
        rows = connection.execute(
            """
            SELECT role, content, created_at
            FROM (
                SELECT id, role, content, created_at
                FROM conversation_messages
                WHERE owner_id = 1
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            )
            ORDER BY created_at ASC
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def save_conversation_turn(user_content: str, assistant_content: str) -> None:
    """Persist one completed user/assistant turn atomically for the local owner."""
    if not isinstance(user_content, str) or not user_content.strip() or len(user_content.strip()) > 8000:
        raise ValueError("conversation_user_message_invalid")
    if not isinstance(assistant_content, str) or not assistant_content.strip() or len(assistant_content.strip()) > 8000:
        raise ValueError("conversation_assistant_message_invalid")
    now = time.time()
    connection = connect_database()
    try:
        _ensure_table(connection)
        connection.execute("BEGIN IMMEDIATE")
        connection.executemany(
            """
            INSERT INTO conversation_messages(owner_id, role, content, created_at)
            VALUES (1, ?, ?, ?)
            """,
            [
                ("user", user_content.strip(), now),
                ("assistant", assistant_content.strip(), now + 0.000001),
            ],
        )
        connection.execute(
            """
            DELETE FROM conversation_messages
            WHERE owner_id = 1 AND id NOT IN (
                SELECT id FROM conversation_messages
                WHERE owner_id = 1
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            )
            """,
            (MAX_HISTORY_MESSAGES,),
        )
        connection.commit()
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
