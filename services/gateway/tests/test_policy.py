import pytest

from app.policy import ActorContext, Decision, RiskTier, ToolRequest, evaluate


@pytest.fixture
def actor():
    return ActorContext("owner-1", "workspace-1", frozenset({"projects:read", "files:write", "email:send"}))


def request(tier=RiskTier.READ_ONLY, scope="projects:read", **kwargs):
    return ToolRequest("example.tool", scope, tier, **kwargs)


def test_scoped_read_only_action_is_allowed(actor):
    assert evaluate(actor, request()).decision == Decision.ALLOW


def test_missing_identity_fails_closed():
    actor = ActorContext(None, "workspace-1", frozenset({"projects:read"}))
    assert evaluate(actor, request()).decision == Decision.DENY


def test_missing_scope_fails_closed(actor):
    assert evaluate(actor, request(scope="admin:all")).decision == Decision.DENY


@pytest.mark.parametrize("tier", [RiskTier.EXTERNAL_SIDE_EFFECT, RiskTier.HIGH_IMPACT])
def test_side_effects_require_explicit_approval(actor, tier):
    result = evaluate(actor, request(tier=tier, scope="email:send"))
    assert result.decision == Decision.APPROVAL_REQUIRED


def test_cross_workspace_request_is_denied(actor):
    assert evaluate(actor, request(workspace_bound=False)).decision == Decision.DENY


def test_incomplete_target_is_denied(actor):
    assert evaluate(actor, request(has_target=False)).decision == Decision.DENY


def test_reversible_scoped_action_is_allowed(actor):
    assert evaluate(actor, request(tier=RiskTier.REVERSIBLE, scope="files:write")).decision == Decision.ALLOW
