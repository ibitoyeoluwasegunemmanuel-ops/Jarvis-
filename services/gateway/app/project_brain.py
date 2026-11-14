"""Owner-scoped project risk register and append-only project memory."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.owner_auth import connect_database

RISK_STATUSES = {"open", "mitigated", "accepted", "closed"}
RISK_SEVERITIES = {"low", "medium", "high", "critical"}
MEMORY_CATEGORIES = {"fact", "preference", "decision", "note", "reference"}


def _ensure_tables(connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS project_risks (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            owner_id INTEGER NOT NULL DEFAULT 1 REFERENCES owner_account(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            severity TEXT NOT NULL CHECK (severity IN ('low','medium','high','critical')),
            mitigation TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open','mitigated','accepted','closed')),
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS project_risks_owner_project
            ON project_risks(owner_id, project_id, updated_at DESC);
        CREATE TABLE IF NOT EXISTS project_memory (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            owner_id INTEGER NOT NULL DEFAULT 1 REFERENCES owner_account(id),
            category TEXT NOT NULL CHECK (category IN ('fact','preference','decision','note','reference')),
            content TEXT NOT NULL,
            source_ref TEXT NOT NULL DEFAULT '',
            confidence REAL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS project_memory_owner_project
            ON project_memory(owner_id, project_id, created_at DESC);
        CREATE TRIGGER IF NOT EXISTS project_memory_no_update
        BEFORE UPDATE ON project_memory
        BEGIN SELECT RAISE(ABORT, 'project_memory_is_append_only'); END;
        CREATE TRIGGER IF NOT EXISTS project_memory_no_delete
        BEFORE DELETE ON project_memory
        BEGIN SELECT RAISE(ABORT, 'project_memory_is_append_only'); END;
        """
    )


def _clean_text(value: str, field: str, limit: int, required: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field}_must_be_text")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field}_required")
    if len(value) > limit:
        raise ValueError(f"{field}_too_long")
    return value


def list_project_risks(project_id: str) -> list[dict[str, Any]]:
    connection = connect_database()
    try:
        _ensure_tables(connection)
        rows = connection.execute(
            """SELECT id, project_id, title, description, severity, mitigation,
                      status, created_at, updated_at
               FROM project_risks WHERE project_id = ? AND owner_id = 1
               ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2 ELSE 3 END, updated_at DESC LIMIT 200""",
            (project_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_project_risk(project_id: str, title: str, description: str,
                        severity: str, mitigation: str = "") -> dict[str, Any] | None:
    title = _clean_text(title, "risk_title", 160, True)
    description = _clean_text(description, "risk_description", 2000)
    mitigation = _clean_text(mitigation, "risk_mitigation", 2000)
    if severity not in RISK_SEVERITIES:
        raise ValueError("risk_severity_invalid")
    risk_id, now = uuid.uuid4().hex, time.time()
    connection = connect_database()
    try:
        _ensure_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        project = connection.execute(
            "SELECT id FROM projects WHERE id = ? AND owner_id = 1", (project_id,)
        ).fetchone()
        if project is None:
            connection.rollback()
            return None
        connection.execute(
            """INSERT INTO project_risks
               (id, project_id, owner_id, title, description, severity, mitigation,
                status, created_at, updated_at)
               VALUES (?, ?, 1, ?, ?, ?, ?, 'open', ?, ?)""",
            (risk_id, project_id, title, description, severity, mitigation, now, now),
        )
        connection.execute(
            """INSERT INTO project_audit_events
               (actor_id, event_type, entity_type, entity_id, details_json, occurred_at)
               VALUES (1, 'risk.created', 'risk', ?, ?, ?)""",
            (risk_id, json.dumps({"project_id": project_id, "title": title,
                                  "severity": severity}, sort_keys=True), now),
        )
        row = connection.execute(
            """SELECT id, project_id, title, description, severity, mitigation,
                      status, created_at, updated_at FROM project_risks WHERE id = ?""",
            (risk_id,),
        ).fetchone()
        connection.commit()
        return dict(row)
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def update_project_risk_status(risk_id: str, status: str) -> dict[str, Any] | None:
    if status not in RISK_STATUSES:
        raise ValueError("risk_status_invalid")
    connection = connect_database()
    try:
        _ensure_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT project_id, status FROM project_risks WHERE id = ? AND owner_id = 1",
            (risk_id,),
        ).fetchone()
        if row is None:
            connection.rollback()
            return None
        previous = str(row["status"])
        now = time.time()
        if previous != status:
            connection.execute(
                "UPDATE project_risks SET status = ?, updated_at = ? WHERE id = ? AND owner_id = 1",
                (status, now, risk_id),
            )
            connection.execute(
                """INSERT INTO project_audit_events
                   (actor_id, event_type, entity_type, entity_id, details_json, occurred_at)
                   VALUES (1, 'risk.status_changed', 'risk', ?, ?, ?)""",
                (risk_id, json.dumps({"from": previous, "to": status}, sort_keys=True), now),
            )
        updated = connection.execute(
            """SELECT id, project_id, title, description, severity, mitigation,
                      status, created_at, updated_at FROM project_risks
               WHERE id = ? AND owner_id = 1""", (risk_id,)
        ).fetchone()
        connection.commit()
        return dict(updated) if updated else None
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def list_project_memory(project_id: str) -> list[dict[str, Any]]:
    connection = connect_database()
    try:
        _ensure_tables(connection)
        rows = connection.execute(
            """SELECT id, project_id, category, content, source_ref, confidence, created_at
               FROM project_memory WHERE project_id = ? AND owner_id = 1
               ORDER BY created_at DESC LIMIT 300""", (project_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_project_memory(project_id: str, category: str, content: str,
                          source_ref: str = "", confidence: float | None = None
                          ) -> dict[str, Any] | None:
    content = _clean_text(content, "memory_content", 4000, True)
    source_ref = _clean_text(source_ref, "memory_source_ref", 1000)
    if category not in MEMORY_CATEGORIES:
        raise ValueError("memory_category_invalid")
    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("memory_confidence_invalid")
        if not 0 <= float(confidence) <= 1:
            raise ValueError("memory_confidence_invalid")
        confidence = float(confidence)
    memory_id, now = uuid.uuid4().hex, time.time()
    connection = connect_database()
    try:
        _ensure_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        project = connection.execute(
            "SELECT id FROM projects WHERE id = ? AND owner_id = 1", (project_id,)
        ).fetchone()
        if project is None:
            connection.rollback()
            return None
        connection.execute(
            """INSERT INTO project_memory
               (id, project_id, owner_id, category, content, source_ref, confidence, created_at)
               VALUES (?, ?, 1, ?, ?, ?, ?, ?)""",
            (memory_id, project_id, category, content, source_ref, confidence, now),
        )
        connection.execute(
            """INSERT INTO project_audit_events
               (actor_id, event_type, entity_type, entity_id, details_json, occurred_at)
               VALUES (1, 'memory.recorded', 'memory', ?, ?, ?)""",
            (memory_id, json.dumps({"project_id": project_id, "category": category},
                                   sort_keys=True), now),
        )
        row = connection.execute(
            """SELECT id, project_id, category, content, source_ref, confidence, created_at
               FROM project_memory WHERE id = ?""", (memory_id,)
        ).fetchone()
        connection.commit()
        return dict(row)
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
