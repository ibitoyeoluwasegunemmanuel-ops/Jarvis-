import pytest
from fastapi.testclient import TestClient

from app.main import app

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


client = TestClient(app)


def test_health_endpoint_reports_gateway_liveness():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "jarvis-gateway"


def test_capabilities_endpoint_does_not_claim_unbuilt_features():
    response = client.get("/v1/system/capabilities")
    assert response.status_code == 200
    capabilities = response.json()["capabilities"]
    assert capabilities["health_check"] is True
    assert capabilities["authorization_policy"] is True
    assert capabilities["agent_execution"] is False
    assert capabilities["persistent_memory"] is False
