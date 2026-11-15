"""Owner-scoped monitoring connector registry and incident inbox.

This registry stores connection metadata only. Provider credentials and live polling
are deliberately not implemented here; secrets must be added through a dedicated vault.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.owner_auth import connect_database

PROVIDERS = {"vercel", "supabase", "github", "manual"}
STATUSES = {"disconnected", "configured", "healthy", "degraded", "error"}
SEVERITIES = {"info", "warning", "critical"}


def _ensure_tables(connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS monitoring_connectors (
            id TEXT PRIMARY KEY,
            owner_id INTEGER NOT NULL DEFAULT 1,
            workspace TEXT NOT NULL,
            provider TEXT NOT NULL,
            display_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'disconnected',
            scopes_json TEXT NOT NULL DEFAULT '[]',
            last_checked_at REAL,
            last_success_at REAL,
            detail TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS monitoring_connectors_owner_workspace
            ON monitoring_connectors(owner_id, workspace, updated_at DESC);
        CREATE TABLE IF NOT EXISTS monitoring_alerts (
            id TEXT PRIMARY KEY,
            owner_id INTEGER NOT NULL DEFAULT 1,
            workspace TEXT NOT NULL,
            connector_id TEXT,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            source_ref TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open',
            first_seen_at REAL NOT NULL,
            last_seen_at REAL NOT NULL,
            acknowledged_at REAL,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS monitoring_alerts_owner_status
            ON monitoring_alerts(owner_id, status, last_seen_at DESC);
        """
    )


def list_connectors() -> list[dict[str, Any]]:
    connection = connect_database()
    try:
        _ensure_tables(connection)
        rows = connection.execute(
            """SELECT id, workspace, provider, display_name, status, scopes_json,
                      last_checked_at, last_success_at, detail, created_at, updated_at
               FROM monitoring_connectors WHERE owner_id = 1
               ORDER BY workspace, display_name"""
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["scopes"] = json.loads(item.pop("scopes_json"))
            result.append(item)
        return result
    finally:
        connection.close()


def register_connector(
    workspace: str, provider: str, display_name: str, scopes: list[str]
) -> dict[str, Any]:
    workspace = workspace.strip()
    display_name = display_name.strip()
    if not workspace or len(workspace) > 80:
        raise ValueError("monitor_workspace_invalid")
    if provider not in PROVIDERS:
        raise ValueError("monitor_provider_unsupported")
    if not display_name or len(display_name) > 120:
        raise ValueError("monitor_display_name_invalid")
    if not isinstance(scopes, list) or len(scopes) > 20 or any(
        not isinstance(scope, str) or not scope.strip() or len(scope) > 80
        for scope in scopes
    ):
        raise ValueError("monitor_scopes_invalid")
    # The first monitoring release is strictly read-only.
    if any(scope.lower().endswith(":write") or "admin" in scope.lower() for scope in scopes):
        raise ValueError("monitoring_connectors_read_only")
    now = time.time()
    connector_id = uuid.uuid4().hex
    connection = connect_database()
    try:
        _ensure_tables(connection)
        connection.execute(
            """INSERT INTO monitoring_connectors
               (id, owner_id, workspace, provider, display_name, status, scopes_json,
                created_at, updated_at)
               VALUES (?, 1, ?, ?, ?, 'disconnected', ?, ?, ?)""",
            (connector_id, workspace, provider, display_name,
             json.dumps(scopes, separators=(",", ":")), now, now),
        )
        connection.commit()
        return next(item for item in list_connectors() if item["id"] == connector_id)
    finally:
        connection.close()


def update_connector_health(
    connector_id: str, status: str, detail: str = "", checked_at: float | None = None
) -> dict[str, Any] | None:
    if status not in STATUSES:
        raise ValueError("monitor_status_invalid")
    if len(detail) > 500:
        raise ValueError("monitor_detail_too_long")
    now = checked_at if checked_at is not None else time.time()
    connection = connect_database()
    try:
        _ensure_tables(connection)
        row = connection.execute(
            "SELECT id FROM monitoring_connectors WHERE id = ? AND owner_id = 1",
            (connector_id,),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            """UPDATE monitoring_connectors
               SET status = ?, detail = ?, last_checked_at = ?,
                   last_success_at = CASE WHEN ? = 'healthy' THEN ? ELSE last_success_at END,
                   updated_at = ?
               WHERE id = ? AND owner_id = 1""",
            (status, detail.strip(), now, status, now, now, connector_id),
        )
        connection.commit()
    finally:
        connection.close()
    return next((item for item in list_connectors() if item["id"] == connector_id), None)


def list_alerts(status: str | None = None) -> list[dict[str, Any]]:
    if status is not None and status not in {"open", "acknowledged", "resolved"}:
        raise ValueError("monitor_alert_status_invalid")
    connection = connect_database()
    try:
        _ensure_tables(connection)
        query = """SELECT id, workspace, connector_id, severity, title, summary,
                          source_ref, status, first_seen_at, last_seen_at,
                          acknowledged_at, created_at
                   FROM monitoring_alerts WHERE owner_id = 1"""
        params: tuple[Any, ...] = ()
        if status:
            query += " AND status = ?"
            params = (status,)
        rows = connection.execute(query + " ORDER BY last_seen_at DESC LIMIT 200", params).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def create_alert(
    workspace: str, severity: str, title: str, summary: str,
    connector_id: str | None = None, source_ref: str = "",
) -> dict[str, Any]:
    if severity not in SEVERITIES:
        raise ValueError("monitor_alert_severity_invalid")
    workspace, title, summary = workspace.strip(), title.strip(), summary.strip()
    if not workspace or len(workspace) > 80 or not title or len(title) > 160:
        raise ValueError("monitor_alert_fields_invalid")
    if not summary or len(summary) > 2000 or len(source_ref) > 1000:
        raise ValueError("monitor_alert_summary_invalid")
    now = time.time()
    connection = connect_database()
    try:
        _ensure_tables(connection)
        # Deduplicate an identical still-open alert in the same workspace.
        existing = connection.execute(
            """SELECT id FROM monitoring_alerts WHERE owner_id = 1
               AND workspace = ? AND title = ? AND status = 'open'
               ORDER BY last_seen_at DESC LIMIT 1""",
            (workspace, title),
        ).fetchone()
        if existing:
            connection.execute(
                "UPDATE monitoring_alerts SET last_seen_at = ?, summary = ? WHERE id = ?",
                (now, summary, existing["id"]),
            )
            alert_id = str(existing["id"])
        else:
            alert_id = uuid.uuid4().hex
            connection.execute(
                """INSERT INTO monitoring_alerts
                   (id, owner_id, workspace, connector_id, severity, title, summary,
                    source_ref, status, first_seen_at, last_seen_at, created_at)
                   VALUES (?, 1, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)""",
                (alert_id, workspace, connector_id, severity, title, summary,
                 source_ref, now, now, now),
            )
        connection.commit()
        row = connection.execute(
            """SELECT id, workspace, connector_id, severity, title, summary,
                      source_ref, status, first_seen_at, last_seen_at,
                      acknowledged_at, created_at
               FROM monitoring_alerts WHERE id = ? AND owner_id = 1""",
            (alert_id,),
        ).fetchone()
        return dict(row)
    finally:
        connection.close()


def acknowledge_alert(alert_id: str) -> dict[str, Any] | None:
    now = time.time()
    connection = connect_database()
    try:
        _ensure_tables(connection)
        connection.execute(
            """UPDATE monitoring_alerts SET status = 'acknowledged', acknowledged_at = ?
               WHERE id = ? AND owner_id = 1 AND status = 'open'""",
            (now, alert_id),
        )
        connection.commit()
        row = connection.execute(
            """SELECT id, workspace, connector_id, severity, title, summary,
                      source_ref, status, first_seen_at, last_seen_at,
                      acknowledged_at, created_at
               FROM monitoring_alerts WHERE id = ? AND owner_id = 1""",
            (alert_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()
