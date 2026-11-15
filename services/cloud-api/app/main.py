"""Separate HTTPS API for JARVIS desktop and mobile clients.

Authentication is delegated to Supabase Auth. The API accepts asymmetric JWTs
only, verifies issuer/audience/signature, and applies a transaction-local user
identity before querying PostgreSQL tables protected by RLS.
"""
from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from functools import lru_cache
from typing import Annotated, Literal

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from jwt import PyJWKClient
from pydantic import BaseModel, Field
from psycopg import connect
from psycopg.rows import dict_row

app = FastAPI(title="JARVIS Cloud API", version="0.1.0", docs_url=None, redoc_url=None)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise HTTPException(status_code=503, detail="cloud_service_not_configured")
    return value


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    return PyJWKClient(_required_env("SUPABASE_JWKS_URL"), cache_jwk_set=True, lifespan=300, timeout=5)


def authenticated_user(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="bearer_token_required")
    token = authorization[7:].strip()
    if not token or len(token) > 8192:
        raise HTTPException(status_code=401, detail="invalid_access_token")
    issuer = _required_env("SUPABASE_JWT_ISSUER")
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token, signing_key.key, algorithms=["ES256", "RS256"],
            audience="authenticated", issuer=issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]}, leeway=30,
        )
        return str(uuid.UUID(claims["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="invalid_access_token") from None


@contextmanager
def user_connection(user_id: str):
    database_url = _required_env("DATABASE_URL")
    # This must be a dedicated NOBYPASSRLS role, never postgres or service-role.
    with connect(database_url, row_factory=dict_row, connect_timeout=5) as connection:
        with connection.transaction():
            connection.execute("SELECT set_config('jarvis.user_id', %s, true)", (user_id,))
            yield connection


UserId = Annotated[str, Depends(authenticated_user)]


class WorkspaceCreate(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="Africa/Lagos", min_length=1, max_length=80)
    locale: str = Field(default="en-NG", min_length=2, max_length=20)


class DeviceRegistration(BaseModel):
    model_config = {"extra": "forbid"}
    workspace_id: uuid.UUID
    device_name: str = Field(min_length=1, max_length=100)
    platform: Literal["windows", "android", "ios", "web"]
    os_version: str = Field(default="", max_length=80)
    app_version: str = Field(default="", max_length=40)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "jarvis-cloud-api", "version": app.version}


@app.get("/v1/workspaces")
def list_workspaces(user_id: UserId) -> list[dict]:
    with user_connection(user_id) as db:
        return db.execute(
            """SELECT w.id, w.name, w.timezone, w.locale, wm.role, w.created_at
               FROM jarvis.workspaces w
               JOIN jarvis.workspace_members wm ON wm.workspace_id = w.id
               WHERE wm.user_id = %s
               ORDER BY w.created_at""",
            (user_id,),
        ).fetchall()


@app.post("/v1/workspaces", status_code=201)
def create_workspace(payload: WorkspaceCreate, user_id: UserId) -> dict:
    workspace_id = uuid.uuid4()
    with user_connection(user_id) as db:
        db.execute(
            """INSERT INTO jarvis.workspaces (id, name, owner_user_id, timezone, locale)
               VALUES (%s, %s, %s, %s, %s)""",
            (workspace_id, payload.name.strip(), user_id, payload.timezone, payload.locale),
        )
        db.execute(
            """INSERT INTO jarvis.workspace_members (workspace_id, user_id, role)
               VALUES (%s, %s, 'owner')""",
            (workspace_id, user_id),
        )
        return db.execute(
            """SELECT id, name, timezone, locale, created_at
               FROM jarvis.workspaces WHERE id = %s""",
            (workspace_id,),
        ).fetchone()


@app.get("/v1/devices")
def list_devices(user_id: UserId, workspace_id: uuid.UUID = Query(...)) -> list[dict]:
    with user_connection(user_id) as db:
        return db.execute(
            """SELECT id, workspace_id, device_name, platform, os_version, app_version,
                      created_at, last_seen_at, revoked_at
               FROM jarvis.devices
               WHERE workspace_id = %s AND revoked_at IS NULL
               ORDER BY last_seen_at DESC NULLS LAST""",
            (workspace_id,),
        ).fetchall()


@app.post("/v1/devices", status_code=201)
def register_device(payload: DeviceRegistration, user_id: UserId) -> dict:
    device_id = uuid.uuid4()
    with user_connection(user_id) as db:
        permitted = db.execute(
            "SELECT id FROM jarvis.workspaces WHERE id = %s", (payload.workspace_id,)
        ).fetchone()
        if permitted is None:
            raise HTTPException(status_code=403, detail="workspace_access_denied")
        return db.execute(
            """INSERT INTO jarvis.devices
               (id, workspace_id, user_id, device_name, platform, os_version, app_version)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               RETURNING id, workspace_id, device_name, platform, os_version, app_version,
                         created_at, last_seen_at""",
            (device_id, payload.workspace_id, user_id, payload.device_name.strip(),
             payload.platform, payload.os_version, payload.app_version),
        ).fetchone()


@app.delete("/v1/devices/{device_id}")
def revoke_device(device_id: uuid.UUID, user_id: UserId) -> dict[str, bool]:
    with user_connection(user_id) as db:
        cursor = db.execute(
            """UPDATE jarvis.devices SET revoked_at = now()
               WHERE id = %s AND user_id = %s AND revoked_at IS NULL""",
            (device_id, user_id),
        )
        if cursor.rowcount != 1:
            raise HTTPException(status_code=404, detail="active_device_not_found")
    return {"revoked": True}


@app.get("/v1/projects")
def list_projects(user_id: UserId, workspace_id: uuid.UUID = Query(...)) -> list[dict]:
    with user_connection(user_id) as db:
        return db.execute(
            """SELECT id, name, slug, description, status, priority, updated_at
               FROM jarvis.projects WHERE workspace_id = %s
               ORDER BY updated_at DESC LIMIT 100""",
            (workspace_id,),
        ).fetchall()


@app.get("/v1/monitoring/alerts")
def list_monitoring_alerts(
    user_id: UserId,
    workspace_id: uuid.UUID = Query(...),
    status: Literal["open", "acknowledged", "resolved"] | None = None,
) -> list[dict]:
    with user_connection(user_id) as db:
        return db.execute(
            """SELECT id, severity, title, summary, source_ref, status,
                      first_seen_at, last_seen_at, acknowledged_at
               FROM jarvis.monitoring_alerts
               WHERE workspace_id = %s AND (%s IS NULL OR status = %s)
               ORDER BY last_seen_at DESC LIMIT 200""",
            (workspace_id, status, status),
        ).fetchall()


@app.get("/v1/workspace/overview")
def workspace_overview(user_id: UserId, workspace_id: uuid.UUID = Query(...)) -> dict:
    with user_connection(user_id) as db:
        workspace = db.execute(
            "SELECT id, name, timezone, locale FROM jarvis.workspaces WHERE id = %s",
            (workspace_id,),
        ).fetchone()
        if workspace is None:
            raise HTTPException(status_code=404, detail="workspace_not_found")
        counts = db.execute(
            """SELECT
                 (SELECT count(*) FROM jarvis.projects WHERE workspace_id = %s) AS projects,
                 (SELECT count(*) FROM jarvis.monitoring_alerts
                    WHERE workspace_id = %s AND status = 'open') AS open_alerts,
                 (SELECT count(*) FROM jarvis.devices
                    WHERE workspace_id = %s AND revoked_at IS NULL) AS active_devices""",
            (workspace_id, workspace_id, workspace_id),
        ).fetchone()
        return {"workspace": workspace, "counts": counts}
