"""Fail-closed authorization policy for JARVIS tool execution.

This module makes a decision only; it never executes a tool. Callers must bind
any approval to the exact action, arguments, actor, and expiry before execution.
"""
from dataclasses import dataclass
from enum import StrEnum


class RiskTier(StrEnum):
    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    EXTERNAL_SIDE_EFFECT = "external_side_effect"
    HIGH_IMPACT = "high_impact"


class Decision(StrEnum):
    ALLOW = "allow"
    APPROVAL_REQUIRED = "approval_required"
    DENY = "deny"


@dataclass(frozen=True)
class ActorContext:
    actor_id: str | None
    workspace_id: str | None
    granted_scopes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    required_scope: str
    risk_tier: RiskTier
    workspace_bound: bool = True
    has_target: bool = True


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str


def evaluate(actor: ActorContext, request: ToolRequest) -> PolicyResult:
    """Evaluate a tool request. Missing identity/scope always fails closed."""
    if not actor.actor_id or not actor.workspace_id:
        return PolicyResult(Decision.DENY, "missing_actor_or_workspace")
    if not request.tool_name or not request.required_scope or not request.has_target:
        return PolicyResult(Decision.DENY, "incomplete_tool_request")
    if request.required_scope not in actor.granted_scopes:
        return PolicyResult(Decision.DENY, "required_scope_not_granted")
    if request.workspace_bound is False:
        return PolicyResult(Decision.DENY, "cross_workspace_access_not_allowed")
    if request.risk_tier in (RiskTier.EXTERNAL_SIDE_EFFECT, RiskTier.HIGH_IMPACT):
        return PolicyResult(Decision.APPROVAL_REQUIRED, "explicit_user_approval_required")
    return PolicyResult(Decision.ALLOW, "scope_and_workspace_validated")
