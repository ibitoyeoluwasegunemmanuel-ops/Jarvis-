"""Trusted, in-process dispatcher for the deliberately small JARVIS action allowlist.

There is no HTTP route for this module. Only trusted orchestration code may call
it; caller identity and scopes must come from the native authenticated runtime,
never from model-generated arguments.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.approval_store import ApprovalError, consume_approval
from app.owner_auth import connect_database
from app.policy import ActorContext, Decision, RiskTier, ToolRequest, evaluate
from app.workspace_store import create_project_task, get_project

MAX_DISPATCH_ARGUMENTS = 16_000


class DispatchError(ValueError):
    """A request was denied or could not be safely dispatched."""


def _create_project_task(arguments: dict[str, Any]) -> dict[str, Any]:
    allowed = {"project_id", "title", "description"}
    if set(arguments) - allowed or not {"project_id", "title"} <= set(arguments):
        raise DispatchError("project_task_arguments_invalid")
    project_id = arguments["project_id"]
    title = arguments["title"]
    description = arguments.get("description", "")
    if not isinstance(project_id, str) or not isinstance(title, str) or not isinstance(description, str):
        raise DispatchError("project_task_arguments_invalid")
    result = create_project_task(project_id, title, description)
    if result is None:
        raise DispatchError("project_not_found")
    return result


_ACTIONS: dict[str, tuple[str, RiskTier, Callable[[dict[str, Any]], dict[str, Any]]]] = {
    "project.task.create": ("projects:write", RiskTier.REVERSIBLE, _create_project_task),
}


def _record_execution_event(
    project_id: str, approval_id: str, action: str, actor_id: str, outcome: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Append a bounded execution lifecycle event to the immutable project log."""
    import json
    import time

    safe_details = {
        "approval_id": approval_id,
        "action": action,
        "outcome": outcome,
        "actor_id": actor_id,
        **(details or {}),
    }
    encoded = json.dumps(safe_details, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > 4_000:
        encoded = json.dumps({
            "approval_id": approval_id, "action": action, "outcome": outcome,
            "detail": "omitted_size_limit",
        }, sort_keys=True, separators=(",", ":"))
    connection = connect_database()
    try:
        connection.execute(
            """INSERT INTO project_audit_events(
                actor_id, event_type, entity_type, entity_id, details_json, occurred_at
            ) VALUES (?, ?, 'action_execution', ?, ?, ?)""",
            (1, f"action_execution.{outcome}", approval_id, encoded, time.time()),
        )
        connection.commit()
    finally:
        connection.close()


def dispatch_approved_action(
    actor: ActorContext,
    approval_id: str,
    nonce: str,
    action: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Re-authorize, bind and consume one approval, then execute one typed action.

    This is intentionally not exposed as an API route. The trusted caller must
    supply an ActorContext created by the authenticated native runtime.
    """
    if not isinstance(arguments, dict):
        raise DispatchError("dispatch_arguments_must_be_object")
    handler_spec = _ACTIONS.get(action)
    if handler_spec is None:
        raise DispatchError("dispatch_action_not_allowlisted")
    required_scope, risk_tier, handler = handler_spec
    project_id = arguments.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise DispatchError("dispatch_target_required")
    if actor.workspace_id != project_id:
        raise DispatchError("dispatch_workspace_mismatch")
    policy = evaluate(
        actor,
        ToolRequest(
            tool_name=action,
            required_scope=required_scope,
            risk_tier=risk_tier,
            workspace_bound=True,
            has_target=True,
        ),
    )
    if policy.decision is Decision.DENY:
        raise DispatchError(f"dispatch_policy_denied:{policy.reason}")

    project = get_project(project_id)
    if project is None:
        raise DispatchError("project_not_found")

    # Consumption is atomic and precedes execution. A failed handler never
    # makes the same approval replayable.
    try:
        consumed = consume_approval(
            approval_id, action, arguments, nonce, expected_project_id=project_id
        )
    except ApprovalError as error:
        raise DispatchError(str(error)) from error
    if consumed is None:
        raise DispatchError("approval_not_found")

    # Persist the start marker before invoking even a local tool.
    _record_execution_event(
        project_id, approval_id, action, actor.actor_id or "unknown", "started"
    )
    try:
        result = handler(consumed["arguments"])
    except Exception as error:
        _record_execution_event(
            project_id, approval_id, action, actor.actor_id or "unknown", "failed",
            {"error_type": type(error).__name__},
        )
        raise
    _record_execution_event(
        project_id, approval_id, action, actor.actor_id or "unknown", "succeeded"
    )
    return {
        "approval_id": approval_id,
        "action": action,
        "status": "executed",
        "result": result,
        "consumed_at": consumed["consumed_at"],
    }
