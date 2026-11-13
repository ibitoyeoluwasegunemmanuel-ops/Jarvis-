"""Single-owner local authentication for the private JARVIS desktop app.

Passwords are Argon2id-hashed; session tokens are stored only as SHA-256 hashes.
The gateway's process token remains a separate first-layer local transport gate.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

SESSION_TTL_SECONDS = 12 * 60 * 60
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256
_PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


class OwnerAuthError(Exception):
    """Base class for expected owner-authentication failures."""


class OwnerAlreadyConfigured(OwnerAuthError):
    pass


class OwnerNotConfigured(OwnerAuthError):
    pass


class InvalidOwnerCredentials(OwnerAuthError):
    pass


class OwnerLoginRateLimited(OwnerAuthError):
    pass


def _data_directory() -> Path:
    configured = os.environ.get("JARVIS_DATA_DIR")
    if configured:
        base = Path(configured).expanduser()
    elif os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        base = base / "JARVIS"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        base = base / "JARVIS"

    base.mkdir(parents=True, exist_ok=True)
    try:
        if os.name != "nt":
            base.chmod(0o700)
    except OSError:
        pass
    return base


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(_data_directory() / "owner-auth.sqlite3", timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS owner_account (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            password_hash TEXT NOT NULL,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS owner_sessions (
            token_hash TEXT PRIMARY KEY,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            revoked_at REAL
        );
        CREATE INDEX IF NOT EXISTS owner_sessions_expiry
            ON owner_sessions(expires_at);
        CREATE TABLE IF NOT EXISTS owner_login_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            owner_id INTEGER NOT NULL DEFAULT 1 REFERENCES owner_account(id),
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'paused', 'completed')),
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS projects_owner_updated
            ON projects(owner_id, updated_at DESC);
        CREATE TABLE IF NOT EXISTS project_audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER NOT NULL DEFAULT 1 REFERENCES owner_account(id),
            event_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            details_json TEXT NOT NULL DEFAULT '{}',
            occurred_at REAL NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS project_audit_events_no_update
        BEFORE UPDATE ON project_audit_events
        BEGIN
            SELECT RAISE(ABORT, 'project_audit_events_are_append_only');
        END;
        CREATE TRIGGER IF NOT EXISTS project_audit_events_no_delete
        BEFORE DELETE ON project_audit_events
        BEGIN
            SELECT RAISE(ABORT, 'project_audit_events_are_append_only');
        END;
        INSERT OR IGNORE INTO owner_login_state(id, failed_attempts, locked_until)
            VALUES (1, 0, 0);
        """
    )
    return connection


def _validate_password(password: str) -> None:
    if not isinstance(password, str):
        raise TypeError("password_must_be_text")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("password_too_short")
    if len(password) > MAX_PASSWORD_LENGTH or "\x00" in password:
        raise ValueError("password_invalid")


def _issue_session(connection: sqlite3.Connection) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = time.time()
    connection.execute(
        "INSERT INTO owner_sessions(token_hash, created_at, expires_at) VALUES (?, ?, ?)",
        (token_hash, now, now + SESSION_TTL_SECONDS),
    )
    return token


def owner_is_configured() -> bool:
    connection = connect_database()
    try:
        row = connection.execute("SELECT 1 FROM owner_account WHERE id = 1").fetchone()
        return row is not None
    finally:
        connection.close()


def setup_owner(password: str) -> str:
    _validate_password(password)
    now = time.time()
    password_hash = _PASSWORD_HASHER.hash(password)
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute("SELECT 1 FROM owner_account WHERE id = 1").fetchone()
        if row is not None:
            connection.rollback()
            raise OwnerAlreadyConfigured("owner_already_configured")

        connection.execute(
            "INSERT INTO owner_account(id, password_hash, created_at, updated_at) "
            "VALUES (1, ?, ?, ?)",
            (password_hash, now, now),
        )
        token = _issue_session(connection)
        connection.commit()
        return token
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def login_owner(password: str) -> str:
    _validate_password(password)
    connection = connect_database()
    try:
        connection.execute("BEGIN IMMEDIATE")
        now = time.time()
        state = connection.execute(
            "SELECT failed_attempts, locked_until FROM owner_login_state WHERE id = 1"
        ).fetchone()
        if state is not None and float(state["locked_until"]) > now:
            connection.rollback()
            raise OwnerLoginRateLimited("owner_login_temporarily_locked")

        account = connection.execute(
            "SELECT password_hash FROM owner_account WHERE id = 1"
        ).fetchone()
        if account is None:
            connection.rollback()
            raise OwnerNotConfigured("owner_setup_required")

        password_hash = str(account["password_hash"])
        try:
            valid = _PASSWORD_HASHER.verify(password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            valid = False

        if not valid:
            failures = int(state["failed_attempts"]) + 1 if state else 1
            locked_until = now + 60 if failures >= 5 else 0
            if locked_until:
                failures = 0
            connection.execute(
                "UPDATE owner_login_state SET failed_attempts = ?, locked_until = ? "
                "WHERE id = 1",
                (failures, locked_until),
            )
            connection.commit()
            raise InvalidOwnerCredentials("invalid_owner_credentials")

        if _PASSWORD_HASHER.check_needs_rehash(password_hash):
            connection.execute(
                "UPDATE owner_account SET password_hash = ?, updated_at = ? WHERE id = 1",
                (_PASSWORD_HASHER.hash(password), now),
            )
        connection.execute(
            "UPDATE owner_login_state SET failed_attempts = 0, locked_until = 0 WHERE id = 1"
        )
        token = _issue_session(connection)
        connection.commit()
        return token
    except Exception:
        if connection.in_transaction:
            connection.rollback()
        raise
    finally:
        connection.close()


def owner_session_is_valid(token: str | None) -> bool:
    if not token or len(token) > 512:
        return False
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection = connect_database()
    try:
        row = connection.execute(
            "SELECT 1 FROM owner_sessions "
            "WHERE token_hash = ? AND revoked_at IS NULL AND expires_at > ?",
            (token_hash, time.time()),
        ).fetchone()
        return row is not None
    finally:
        connection.close()


def revoke_owner_session(token: str | None) -> bool:
    if not token or len(token) > 512:
        return False
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection = connect_database()
    try:
        cursor = connection.execute(
            "UPDATE owner_sessions SET revoked_at = ? "
            "WHERE token_hash = ? AND revoked_at IS NULL",
            (time.time(), token_hash),
        )
        connection.commit()
        return cursor.rowcount == 1
    finally:
        connection.close()
