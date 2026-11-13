"""Owner-scoped persistence for local JARVIS projects."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.owner_auth import connect_database

MAX_PROJECT_NAME_LENGTH = 120
MAX_PROJECT_DESCRIPTION_LENGTH = 2000


def _normalise_project_input(name: str, description: str) -> tuple[str, str]:
    if not isinstance(name, str):
        raise TypeError("project_name_must_be_text")
    if not isinstance(description, str):
        raise TypeError("project_description_must_be_text")

    clean_name = name.strip()
    clean_description = description.strip()
    if not clean_name:
        raise ValueError("project_name_required")
    if len(clean_name) > MAX_PROJECT_NAME_LENGTH:
        raise ValueError("project_name_too_long")
    if len(clean_description) > MAX_PROJECT_DESCRIPTION_LENGTH:
        raise ValueError("project_description_too_long")
    return clean_name, clean_description


def list_projects() -> list[dict[str, Any]]:
    """Return the current local owner's projects, newest activity first."""
    connection = connect_database()
    try:
        rows = connection.execute(
            """
            SELECT id, name, description, status, created_at, updated_at
            FROM projects
            WHERE owner_id = 1
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 100
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_project(project_id: str) -> dict[str, Any] | None:
    """Fetch one project belonging to the local owner only."""
    if not isinstance(project_id, str) or not project_id or len(project_id) > 64:
        return None

    connection = connect_database()
    try:
        row = connection.execute(
            """
            SELECT id, name, description, status, created_at, updated_at
            FROM projects
            WHERE id = ? AND owner_id = 1
            """,
            (project_id,),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        connection.close()


def create_project(name: str, description: str = "") -> dict[str, Any]:
    """Create a local owner project and its immutable creation audit event."""
    clean_name, clean_description = _normalise_project_input(name, description)
    project_id = uuid.uuid4().hex
    now = time.time()

    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            INSERT INTO projects(
                id, owner_id, name, description, status, created_at, updated_at
            ) VALUES (?, 1, ?, ?, 'active', ?, ?)
            """,
            (project_id, clean_name, clean_description, now, now),
        )
        connection.execute(
            """
            INSERT INTO project_audit_events(
                actor_id, event_type, entity_type, entity_id, details_json, occurred_at
            ) VALUES (1, 'project.created', 'project', ?, ?, ?)
            """,
            (
                project_id,
                json.dumps({"name": clean_name}, separators=(",", ":"), sort_keys=True),
                now,
            ),
        )
        row = connection.execute(
            """
            SELECT id, name, description, status, created_at, updated_at
            FROM projects
            WHERE id = ? AND owner_id = 1
            """,
            (project_id,),
        ).fetchone()
        connection.commit()
        if row is None:
            raise RuntimeError("project_create_failed")
        return dict(row)
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
