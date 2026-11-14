"""Owner-initiated execution endpoint for the restricted local dispatcher.

The caller cannot provide actor identity or scopes. They are derived only after
the native gateway and owner-session middleware authenticate the request.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.approval_store import ApprovalError
from app.dispatcher import DispatchError, dispatch_approved_action
from app.policy import ActorContext
from app.approval_routes import _require_owner

router = APIRouter(prefix="/v1/execution", tags=["execution"])


class ExecuteApprovedAction(BaseModel):
    model_config = {"extra": "forbid"}

    approval_id: str = Field(min_length=1, max_length=64)
    nonce: str = Field(min_length=1, max_length=256)
    action: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any]


@router.post("/approved", dependencies=[Depends(_require_owner)])
def execute_approved_action(payload: ExecuteApprovedAction) -> dict[str, Any]:
    """Execute one approved allowlisted action as the authenticated local owner."""
    project_id = payload.arguments.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise HTTPException(status_code=422, detail="execution_target_required")

    # This local single-owner installation has one authenticated principal.
    # Identity and scope are server-derived; neither is accepted from the caller.
    actor = ActorContext(
        actor_id="owner:local",
        workspace_id=project_id,
        granted_scopes=frozenset({"projects:write"}),
    )
    try:
        return dispatch_approved_action(
            actor, payload.approval_id, payload.nonce,
            payload.action, payload.arguments,
        )
    except DispatchError as error:
        message = str(error)
        status = 404 if message in {"approval_not_found", "project_not_found"} else 409
        raise HTTPException(status_code=status, detail=message) from error
