"""Owner-authenticated API for reviewing action-bound approvals.

This API records requests and owner decisions. It deliberately exposes no
HTTP execution/consumption endpoint; consumption belongs inside a future
trusted execution dispatcher.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.approval_store import (
    ApprovalError,
    decide_approval,
    list_project_approvals,
    request_approval,
)
from app.owner_auth import owner_session_is_valid

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


def _require_owner(request: Request) -> None:
    token = request.headers.get("X-Jarvis-Owner-Session")
    if not owner_session_is_valid(token):
        raise HTTPException(status_code=401, detail="valid_owner_session_required")


class ApprovalRequest(BaseModel):
    model_config = {"extra": "forbid"}

    project_id: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any]
    ttl_seconds: int = Field(default=300, ge=1, le=900)


class ApprovalDecision(BaseModel):
    model_config = {"extra": "forbid"}

    approve: bool


@router.get("/{project_id}", dependencies=[Depends(_require_owner)])
def approvals_for_project(project_id: str) -> list[dict[str, Any]]:
    result = list_project_approvals(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return result


@router.post("", status_code=201, dependencies=[Depends(_require_owner)])
def create_approval(payload: ApprovalRequest) -> dict[str, Any]:
    try:
        result = request_approval(
            payload.project_id, payload.action, payload.arguments,
            requester="owner", ttl_seconds=payload.ttl_seconds,
        )
    except ApprovalError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="project_not_found")
    return result


@router.post("/{approval_id}/decision", dependencies=[Depends(_require_owner)])
def review_approval(approval_id: str, payload: ApprovalDecision) -> dict[str, Any]:
    try:
        result = decide_approval(approval_id, payload.approve)
    except ApprovalError as error:
        status = 409 if str(error) in {
            "approval_not_pending", "approval_expired"
        } else 422
        raise HTTPException(status_code=status, detail=str(error)) from error
    if result is None:
        raise HTTPException(status_code=404, detail="approval_not_found")
    return result
