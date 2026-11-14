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

def update_project_status(project_id: str, status: str) -> dict[str, Any] | None:
    """Change a local project status and append an immutable audit event."""
    allowed_statuses = {"active", "paused", "completed"}
    if status not in allowed_statuses:
        raise ValueError("project_status_invalid")
    if not isinstance(project_id, str) or not project_id or len(project_id) > 64:
        return None

    now = time.time()
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT status FROM projects WHERE id = ? AND owner_id = 1",
            (project_id,),
        ).fetchone()
        if row is None:
            connection.rollback()
            return None

        previous_status = str(row["status"])
        if previous_status != status:
            connection.execute(
                """
                UPDATE projects
                SET status = ?, updated_at = ?
                WHERE id = ? AND owner_id = 1
                """,
                (status, now, project_id),
            )
            connection.execute(
                """
                INSERT INTO project_audit_events(
                    actor_id, event_type, entity_type, entity_id, details_json, occurred_at
                ) VALUES (1, 'project.status_changed', 'project', ?, ?, ?)
                """,
                (
                    project_id,
                    json.dumps(
                        {"from": previous_status, "to": status},
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    now,
                ),
            )

        updated = connection.execute(
            """
            SELECT id, name, description, status, created_at, updated_at
            FROM projects
            WHERE id = ? AND owner_id = 1
            """,
            (project_id,),
        ).fetchone()
        connection.commit()
        return dict(updated) if updated is not None else None
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


MAX_TASK_TITLE_LENGTH = 160
MAX_TASK_DESCRIPTION_LENGTH = 2000


def _normalise_task_input(title: str, description: str) -> tuple[str, str]:
    if not isinstance(title, str):
        raise TypeError("task_title_must_be_text")
    if not isinstance(description, str):
        raise TypeError("task_description_must_be_text")

    clean_title = title.strip()
    clean_description = description.strip()
    if not clean_title:
        raise ValueError("task_title_required")
    if len(clean_title) > MAX_TASK_TITLE_LENGTH:
        raise ValueError("task_title_too_long")
    if len(clean_description) > MAX_TASK_DESCRIPTION_LENGTH:
        raise ValueError("task_description_too_long")
    return clean_title, clean_description


def list_project_tasks(project_id: str) -> list[dict[str, Any]]:
    """List tasks only when they belong to the local owner and requested project."""
    if not isinstance(project_id, str) or not project_id or len(project_id) > 64:
        return []

    connection = connect_database()
    try:
        rows = connection.execute(
            """
            SELECT id, project_id, title, description, status, created_at, updated_at
            FROM project_tasks
            WHERE project_id = ? AND owner_id = 1
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 200
            """,
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_project_task(
    project_id: str, title: str, description: str = ""
) -> dict[str, Any] | None:
    """Create a task under an owner project and append an immutable audit event."""
    if not isinstance(project_id, str) or not project_id or len(project_id) > 64:
        return None
    clean_title, clean_description = _normalise_task_input(title, description)
    task_id = uuid.uuid4().hex
    now = time.time()

    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        project = connection.execute(
            "SELECT id FROM projects WHERE id = ? AND owner_id = 1",
            (project_id,),
        ).fetchone()
        if project is None:
            connection.rollback()
            return None

        connection.execute(
            """
            INSERT INTO project_tasks(
                id, project_id, owner_id, title, description, status, created_at, updated_at
            ) VALUES (?, ?, 1, ?, ?, 'open', ?, ?)
            """,
            (task_id, project_id, clean_title, clean_description, now, now),
        )
        connection.execute(
            """
            INSERT INTO project_audit_events(
                actor_id, event_type, entity_type, entity_id, details_json, occurred_at
            ) VALUES (1, 'task.created', 'task', ?, ?, ?)
            """,
            (
                task_id,
                json.dumps(
                    {"project_id": project_id, "title": clean_title},
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                now,
            ),
        )
        row = connection.execute(
            """
            SELECT id, project_id, title, description, status, created_at, updated_at
            FROM project_tasks
            WHERE id = ? AND owner_id = 1
            """,
            (task_id,),
        ).fetchone()
        connection.commit()
        if row is None:
            raise RuntimeError("project_task_create_failed")
        return dict(row)
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def update_project_task_status(task_id: str, status: str) -> dict[str, Any] | None:
    """Update a task status and append an audit event only when it changes."""
    allowed_statuses = {"open", "in_progress", "done"}
    if status not in allowed_statuses:
        raise ValueError("project_task_status_invalid")
    if not isinstance(task_id, str) or not task_id or len(task_id) > 64:
        return None

    now = time.time()
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT status FROM project_tasks WHERE id = ? AND owner_id = 1",
            (task_id,),
        ).fetchone()
        if row is None:
            connection.rollback()
            return None

        previous_status = str(row["status"])
        if previous_status != status:
            connection.execute(
                """
                UPDATE project_tasks
                SET status = ?, updated_at = ?
                WHERE id = ? AND owner_id = 1
                """,
                (status, now, task_id),
            )
            connection.execute(
                """
                INSERT INTO project_audit_events(
                    actor_id, event_type, entity_type, entity_id, details_json, occurred_at
                ) VALUES (1, 'task.status_changed', 'task', ?, ?, ?)
                """,
                (
                    task_id,
                    json.dumps(
                        {"from": previous_status, "to": status},
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    now,
                ),
            )

        updated = connection.execute(
            """
            SELECT id, project_id, title, description, status, created_at, updated_at
            FROM project_tasks
            WHERE id = ? AND owner_id = 1
            """,
            (task_id,),
        ).fetchone()
        connection.commit()
        return dict(updated) if updated is not None else None
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def list_project_activity(project_id: str) -> list[dict[str, Any]]:
    """Return a recent, owner-scoped audit timeline for a project and its tasks."""
    if not isinstance(project_id, str) or not project_id or len(project_id) > 64:
        return []

    connection = connect_database()
    try:
        rows = connection.execute(
            """
            SELECT id, event_type, entity_type, entity_id, details_json, occurred_at
            FROM project_audit_events
            WHERE (
                entity_type = 'project'
                AND entity_id = ?
            ) OR (
                entity_type = 'task'
                AND entity_id IN (
                    SELECT id FROM project_tasks
                    WHERE project_id = ? AND owner_id = 1
                )
            )
            ORDER BY occurred_at DESC, id DESC
            LIMIT 100
            """,
            (project_id, project_id),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


MAX_DECISION_TITLE_LENGTH = 160
MAX_DECISION_TEXT_LENGTH = 4000
MAX_DECISION_RATIONALE_LENGTH = 4000
MAX_DECISION_SOURCE_REF_LENGTH = 1000


def _normalise_decision_input(
    title: str, decision: str, rationale: str, source_ref: str
) -> tuple[str, str, str, str]:
    values = {
        "title": title,
        "decision": decision,
        "rationale": rationale,
        "source_ref": source_ref,
    }
    if any(not isinstance(value, str) for value in values.values()):
        raise TypeError("project_decision_fields_must_be_text")

    clean_title = title.strip()
    clean_decision = decision.strip()
    clean_rationale = rationale.strip()
    clean_source_ref = source_ref.strip()
    if not clean_title:
        raise ValueError("project_decision_title_required")
    if not clean_decision:
        raise ValueError("project_decision_text_required")
    if len(clean_title) > MAX_DECISION_TITLE_LENGTH:
        raise ValueError("project_decision_title_too_long")
    if len(clean_decision) > MAX_DECISION_TEXT_LENGTH:
        raise ValueError("project_decision_text_too_long")
    if len(clean_rationale) > MAX_DECISION_RATIONALE_LENGTH:
        raise ValueError("project_decision_rationale_too_long")
    if len(clean_source_ref) > MAX_DECISION_SOURCE_REF_LENGTH:
        raise ValueError("project_decision_source_ref_too_long")
    return clean_title, clean_decision, clean_rationale, clean_source_ref


def list_project_decisions(project_id: str) -> list[dict[str, Any]]:
    """List append-only decisions belonging to the local owner's project."""
    if not isinstance(project_id, str) or not project_id or len(project_id) > 64:
        return []

    connection = connect_database()
    try:
        rows = connection.execute(
            """
            SELECT id, project_id, title, decision, rationale, source_ref,
                   decided_at, created_at
            FROM project_decisions
            WHERE project_id = ? AND owner_id = 1
            ORDER BY decided_at DESC, created_at DESC
            LIMIT 200
            """,
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_project_decision(
    project_id: str,
    title: str,
    decision: str,
    rationale: str = "",
    source_ref: str = "",
) -> dict[str, Any] | None:
    """Record an immutable project decision and append its audit event."""
    if not isinstance(project_id, str) or not project_id or len(project_id) > 64:
        return None
    clean_title, clean_decision, clean_rationale, clean_source_ref = (
        _normalise_decision_input(title, decision, rationale, source_ref)
    )
    decision_id = uuid.uuid4().hex
    now = time.time()

    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        project = connection.execute(
            "SELECT id FROM projects WHERE id = ? AND owner_id = 1",
            (project_id,),
        ).fetchone()
        if project is None:
            connection.rollback()
            return None

        connection.execute(
            """
            INSERT INTO project_decisions(
                id, project_id, owner_id, title, decision, rationale,
                source_ref, decided_at, created_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                project_id,
                clean_title,
                clean_decision,
                clean_rationale,
                clean_source_ref,
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO project_audit_events(
                actor_id, event_type, entity_type, entity_id, details_json, occurred_at
            ) VALUES (1, 'decision.recorded', 'decision', ?, ?, ?)
            """,
            (
                decision_id,
                json.dumps(
                    {"project_id": project_id, "title": clean_title},
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                now,
            ),
        )
        row = connection.execute(
            """
            SELECT id, project_id, title, decision, rationale, source_ref,
                   decided_at, created_at
            FROM project_decisions
            WHERE id = ? AND owner_id = 1
            """,
            (decision_id,),
        ).fetchone()
        connection.commit()
        if row is None:
            raise RuntimeError("project_decision_create_failed")
        return dict(row)
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
