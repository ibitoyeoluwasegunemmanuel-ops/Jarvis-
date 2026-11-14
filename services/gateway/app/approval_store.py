"""Single-owner, action-bound approval records.

Approvals authorize one exact action payload for one project and are single-use.
They do not execute the action; the execution layer must re-check policy.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time
import uuid
from typing import Any

from app.owner_auth import connect_database

MAX_TTL_SECONDS = 15 * 60
MAX_ACTION_LENGTH = 120
MAX_CANONICAL_ARGUMENTS = 16_000


class ApprovalError(ValueError):
    """Expected approval validation or lifecycle failure."""


def _canonical_arguments(arguments: dict[str, Any]) -> tuple[str, str]:
    if not isinstance(arguments, dict):
        raise ApprovalError("approval_arguments_must_be_object")
    try:
        canonical = json.dumps(
            arguments, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ApprovalError("approval_arguments_invalid") from error
    if len(canonical.encode("utf-8")) > MAX_CANONICAL_ARGUMENTS:
        raise ApprovalError("approval_arguments_too_large")
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return canonical, digest


def _ensure_tables(connection) -> None:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS action_approvals (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            owner_id INTEGER NOT NULL DEFAULT 1 REFERENCES owner_account(id),
            action TEXT NOT NULL,
            arguments_json TEXT NOT NULL,
            arguments_hash TEXT NOT NULL,
            requester TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('pending', 'approved', 'denied', 'consumed', 'expired')
            ),
            nonce_hash TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            decided_at REAL,
            consumed_at REAL
        )"""
    )
    connection.execute(
        """CREATE INDEX IF NOT EXISTS action_approvals_project_created
           ON action_approvals(owner_id, project_id, created_at DESC)"""
    )
    connection.execute(
        """CREATE TRIGGER IF NOT EXISTS action_approvals_no_delete
           BEFORE DELETE ON action_approvals
           BEGIN
               SELECT RAISE(ABORT, 'action_approvals_are_append_only');
           END"""
    )


def _audit(connection, event: str, approval_id: str, project_id: str, details: dict) -> None:
    connection.execute(
        """INSERT INTO project_audit_events(
            actor_id, event_type, entity_type, entity_id, details_json, occurred_at
        ) VALUES (1, ?, 'approval', ?, ?, ?)""",
        (event, approval_id, json.dumps(
            {"project_id": project_id, **details}, sort_keys=True, separators=(",", ":")
        ), time.time()),
    )


def request_approval(
    project_id: str, action: str, arguments: dict[str, Any],
    requester: str = "owner", ttl_seconds: int = 300,
) -> dict[str, Any] | None:
    if not isinstance(project_id, str) or not project_id or len(project_id) > 64:
        return None
    if not isinstance(action, str) or not action.strip() or len(action) > MAX_ACTION_LENGTH:
        raise ApprovalError("approval_action_invalid")
    if not isinstance(requester, str) or not requester.strip() or len(requester) > 120:
        raise ApprovalError("approval_requester_invalid")
    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ApprovalError("approval_ttl_invalid")

    canonical, args_hash = _canonical_arguments(arguments)
    approval_id = uuid.uuid4().hex
    nonce = secrets.token_urlsafe(32)
    now = time.time()
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_tables(connection)
        exists = connection.execute(
            "SELECT 1 FROM projects WHERE id = ? AND owner_id = 1", (project_id,)
        ).fetchone()
        if exists is None:
            connection.rollback()
            return None
        expires = now + ttl_seconds
        connection.execute(
            """INSERT INTO action_approvals(
                id, project_id, owner_id, action, arguments_json, arguments_hash,
                requester, status, nonce_hash, created_at, expires_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (approval_id, project_id, action.strip(), canonical, args_hash,
             requester.strip(), hashlib.sha256(nonce.encode()).hexdigest(), now, expires),
        )
        _audit(connection, "approval.requested", approval_id, project_id,
               {"action": action.strip(), "arguments_hash": args_hash, "requester": requester.strip()})
        connection.commit()
        return {
            "id": approval_id, "project_id": project_id, "action": action.strip(),
            "arguments": arguments, "arguments_hash": args_hash, "requester": requester.strip(),
            "status": "pending", "created_at": now, "expires_at": expires, "nonce": nonce,
        }
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def decide_approval(approval_id: str, approve: bool) -> dict[str, Any] | None:
    if not isinstance(approval_id, str) or not approval_id or len(approval_id) > 64:
        return None
    if not isinstance(approve, bool):
        raise ApprovalError("approval_decision_invalid")
    now = time.time()
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_tables(connection)
        row = connection.execute(
            "SELECT project_id, action, status, expires_at FROM action_approvals "
            "WHERE id = ? AND owner_id = 1", (approval_id,)
        ).fetchone()
        if row is None:
            connection.rollback()
            return None
        if row["status"] != "pending":
            connection.rollback()
            raise ApprovalError("approval_not_pending")
        if float(row["expires_at"]) <= now:
            connection.execute(
                "UPDATE action_approvals SET status = 'expired', decided_at = ? WHERE id = ?",
                (now, approval_id),
            )
            _audit(connection, "approval.expired", approval_id, row["project_id"], {"action": row["action"]})
            connection.commit()
            raise ApprovalError("approval_expired")
        status = "approved" if approve else "denied"
        connection.execute(
            "UPDATE action_approvals SET status = ?, decided_at = ? WHERE id = ?",
            (status, now, approval_id),
        )
        _audit(connection, f"approval.{status}", approval_id, row["project_id"], {"action": row["action"]})
        connection.commit()
        return {"id": approval_id, "status": status, "decided_at": now}
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def consume_approval(
    approval_id: str, action: str, arguments: dict[str, Any], nonce: str,
) -> dict[str, Any] | None:
    """Atomically consume an approved record for the exact action, args and nonce."""
    if not all(isinstance(value, str) and value and len(value) <= 256
               for value in (approval_id, action, nonce)):
        raise ApprovalError("approval_consumption_input_invalid")
    _, args_hash = _canonical_arguments(arguments)
    now = time.time()
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _ensure_tables(connection)
        row = connection.execute(
            """SELECT project_id, action, arguments_json, arguments_hash,
                      status, nonce_hash, expires_at
               FROM action_approvals WHERE id = ? AND owner_id = 1""",
            (approval_id,),
        ).fetchone()
        if row is None:
            connection.rollback()
            return None
        if row["status"] != "approved":
            connection.rollback()
            raise ApprovalError("approval_not_approved_or_already_used")
        if float(row["expires_at"]) <= now:
            connection.execute(
                "UPDATE action_approvals SET status = 'expired' WHERE id = ?", (approval_id,)
            )
            _audit(connection, "approval.expired", approval_id, row["project_id"], {"action": row["action"]})
            connection.commit()
            raise ApprovalError("approval_expired")
        nonce_hash = hashlib.sha256(nonce.encode()).hexdigest()
        if (not secrets.compare_digest(str(row["nonce_hash"]), nonce_hash)
            or not secrets.compare_digest(str(row["action"]), action)
            or not secrets.compare_digest(str(row["arguments_hash"]), args_hash)):
            connection.rollback()
            raise ApprovalError("approval_binding_mismatch")
        connection.execute(
            "UPDATE action_approvals SET status = 'consumed', consumed_at = ? WHERE id = ?",
            (now, approval_id),
        )
        _audit(connection, "approval.consumed", approval_id, row["project_id"],
               {"action": action, "arguments_hash": args_hash})
        connection.commit()
        return {
            "id": approval_id, "project_id": row["project_id"], "action": action,
            "arguments": json.loads(str(row["arguments_json"])), "consumed_at": now,
        }
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()
