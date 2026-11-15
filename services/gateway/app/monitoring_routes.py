"""Owner-authenticated monitoring registry and alert inbox routes."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.owner_auth import owner_session_is_valid
from fastapi import HTTPException, Request
from app.monitoring_store import (
    acknowledge_alert,
    create_alert,
    list_alerts,
    list_connectors,
    register_connector,
    update_connector_health,
)

router = APIRouter(prefix="/v1/monitoring", tags=["monitoring"])


class ConnectorCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    workspace: str = Field(min_length=1, max_length=80)
    provider: Literal["vercel", "supabase", "github", "manual"]
    display_name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=list, max_length=20)


class ConnectorHealthRequest(BaseModel):
    model_config = {"extra": "forbid"}
    status: Literal["disconnected", "configured", "healthy", "degraded", "error"]
    detail: str = Field(default="", max_length=500)


class AlertCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}
    workspace: str = Field(min_length=1, max_length=80)
    severity: Literal["info", "warning", "critical"]
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=2000)
    connector_id: str | None = Field(default=None, max_length=64)
    source_ref: str = Field(default="", max_length=1000)


@router.get("/connectors")
def connectors_list(_: None = Depends(require_owner_session)) -> list[dict]:
    return list_connectors()


@router.post("/connectors", status_code=201)
def connector_create(
    payload: ConnectorCreateRequest, _: None = Depends(require_owner_session)
) -> dict:
    try:
        return register_connector(
            payload.workspace, payload.provider, payload.display_name, payload.scopes
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.patch("/connectors/{connector_id}/health")
def connector_health_update(
    connector_id: str,
    payload: ConnectorHealthRequest,
    _: None = Depends(require_owner_session),
) -> dict:
    try:
        result = update_connector_health(connector_id, payload.status, payload.detail)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="monitor_connector_not_found")
    return result


@router.get("/alerts")
def alerts_list(
    status: Literal["open", "acknowledged", "resolved"] | None = None,
    _: None = Depends(require_owner_session),
) -> list[dict]:
    return list_alerts(status)


@router.post("/alerts", status_code=201)
def alert_create(
    payload: AlertCreateRequest, _: None = Depends(require_owner_session)
) -> dict:
    try:
        return create_alert(
            payload.workspace, payload.severity, payload.title, payload.summary,
            payload.connector_id, payload.source_ref,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/alerts/{alert_id}/acknowledge")
def alert_acknowledge(
    alert_id: str, _: None = Depends(require_owner_session)
) -> dict:
    result = acknowledge_alert(alert_id)
    if result is None:
        raise HTTPException(status_code=404, detail="monitor_alert_not_found")
    return result
