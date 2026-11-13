import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.owner_auth import connect_database
from app.policy import ActorContext, Decision, RiskTier, ToolRequest, evaluate


@pytest.fixture
def actor():
    return ActorContext(
        "owner-1",
        "workspace-1",
        frozenset({"projects:read", "files:write", "email:send"}),
    )


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


def test_protected_endpoint_rejects_missing_session(monkeypatch):
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "a" * 40)
    response = client.get("/v1/system/capabilities")
    assert response.status_code == 401
    assert response.json()["detail"] == "valid_gateway_session_required"


def test_protected_endpoint_rejects_invalid_session(monkeypatch):
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "a" * 40)
    response = client.get(
        "/v1/system/capabilities",
        headers={"X-Jarvis-Session": "wrong-token"},
    )
    assert response.status_code == 401


def test_protected_endpoint_fails_closed_when_session_is_not_configured(monkeypatch):
    monkeypatch.delenv("JARVIS_SESSION_TOKEN", raising=False)
    response = client.get(
        "/v1/system/capabilities",
        headers={"X-Jarvis-Session": "a" * 40},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "gateway_session_not_configured"


def test_capabilities_endpoint_requires_session_and_reports_unbuilt_features(monkeypatch, tmp_path):
    token = "jarvis-test-session-token-" + ("x" * 40)
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", token)
    response = client.get(
        "/v1/system/capabilities",
        headers={"X-Jarvis-Session": token},
    )
    assert response.status_code == 200
    capabilities = response.json()["capabilities"]
    security = response.json()["security"]
    assert capabilities["health_check"] is True
    assert capabilities["authorization_policy"] is True
    assert capabilities["gateway_session_authentication"] is True
    assert capabilities["agent_execution"] is False
    assert capabilities["persistent_memory"] is False
    assert security["gateway_session_configured"] is True
    assert security["owner_authentication_configured"] is False
    assert security["owner_session_authenticated"] is False

def test_tauri_webview_origin_allows_session_header_preflight():
    response = client.options(
        "/v1/system/capabilities",
        headers={
            "Origin": "http://tauri.localhost",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Jarvis-Session",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://tauri.localhost"
    assert "x-jarvis-session" in response.headers["access-control-allow-headers"].lower()

def _process_headers(token="test-gateway-session-" + ("g" * 40)):
    return {"X-Jarvis-Session": token}


def test_owner_setup_creates_single_account_and_native_session(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-" + ("g" * 40))
    headers = _process_headers()

    status = client.get("/v1/auth/status", headers=headers)
    assert status.status_code == 200
    assert status.json() == {
        "owner_configured": False,
        "setup_required": True,
        "authenticated": False,
    }

    response = client.post(
        "/v1/auth/setup",
        headers=headers,
        json={"password": "correct-horse-battery-7"},
    )
    assert response.status_code == 200
    session_token = response.json()["owner_session_token"]
    assert len(session_token) >= 40

    authenticated = client.get(
        "/v1/auth/status",
        headers={**headers, "X-Jarvis-Owner-Session": session_token},
    )
    assert authenticated.status_code == 200
    assert authenticated.json()["authenticated"] is True

    second_setup = client.post(
        "/v1/auth/setup",
        headers=headers,
        json={"password": "another-valid-password-9"},
    )
    assert second_setup.status_code == 409


def test_owner_login_rejects_wrong_password_and_accepts_correct_password(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-" + ("g" * 40))
    headers = _process_headers()
    password = "correct-horse-battery-7"

    setup = client.post("/v1/auth/setup", headers=headers, json={"password": password})
    assert setup.status_code == 200

    invalid = client.post(
        "/v1/auth/login",
        headers=headers,
        json={"password": "incorrect-password-8"},
    )
    assert invalid.status_code == 401

    login = client.post(
        "/v1/auth/login",
        headers=headers,
        json={"password": password},
    )
    assert login.status_code == 200
    token = login.json()["owner_session_token"]
    status = client.get(
        "/v1/auth/status",
        headers={**headers, "X-Jarvis-Owner-Session": token},
    )
    assert status.json()["authenticated"] is True


def test_owner_login_is_rate_limited_after_five_failures(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-" + ("g" * 40))
    headers = _process_headers()
    setup = client.post(
        "/v1/auth/setup",
        headers=headers,
        json={"password": "correct-horse-battery-7"},
    )
    assert setup.status_code == 200

    for _ in range(5):
        failed = client.post(
            "/v1/auth/login",
            headers=headers,
            json={"password": "wrong-password-attempt-9"},
        )
        assert failed.status_code == 401

    limited = client.post(
        "/v1/auth/login",
        headers=headers,
        json={"password": "correct-horse-battery-7"},
    )
    assert limited.status_code == 429


def test_owner_logout_revokes_session(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-" + ("g" * 40))
    headers = _process_headers()
    setup = client.post(
        "/v1/auth/setup",
        headers=headers,
        json={"password": "correct-horse-battery-7"},
    )
    token = setup.json()["owner_session_token"]

    logout = client.post(
        "/v1/auth/logout",
        headers={**headers, "X-Jarvis-Owner-Session": token},
    )
    assert logout.status_code == 200
    assert logout.json()["revoked"] is True

    status = client.get(
        "/v1/auth/status",
        headers={**headers, "X-Jarvis-Owner-Session": token},
    )
    assert status.json()["authenticated"] is False


def test_owner_auth_endpoints_still_require_gateway_process_session(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-" + ("g" * 40))
    response = client.get("/v1/auth/status")
    assert response.status_code == 401


def test_owner_password_must_meet_minimum_length(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-" + ("g" * 40))
    response = client.post(
        "/v1/auth/setup",
        headers=_process_headers(),
        json={"password": "short"},
    )
    assert response.status_code == 422

def _create_owner_session(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    process = "test-gateway-session-" + ("g" * 40)
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", process)
    process_headers = {"X-Jarvis-Session": process}
    setup = client.post(
        "/v1/auth/setup",
        headers=process_headers,
        json={"password": "correct-horse-battery-7"},
    )
    assert setup.status_code == 200
    return {
        **process_headers,
        "X-Jarvis-Owner-Session": setup.json()["owner_session_token"],
    }


def test_project_routes_require_a_valid_owner_session(monkeypatch, tmp_path):
    process = "test-gateway-session-" + ("g" * 40)
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", process)
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    headers = {"X-Jarvis-Session": process}

    denied = client.get("/v1/projects", headers=headers)
    assert denied.status_code == 401
    assert denied.json()["detail"] == "valid_owner_session_required"

    owner_headers = _create_owner_session(monkeypatch, tmp_path)
    allowed = client.get("/v1/projects", headers=owner_headers)
    assert allowed.status_code == 200
    assert allowed.json() == []


def test_projects_persist_under_owner_and_write_immutable_audit_event(
    monkeypatch, tmp_path
):
    headers = _create_owner_session(monkeypatch, tmp_path)
    response = client.post(
        "/v1/projects",
        headers=headers,
        json={
            "name": "Drive Secure",
            "description": "Connected vehicle security platform",
        },
    )
    assert response.status_code == 201
    project = response.json()
    assert project["name"] == "Drive Secure"
    assert project["description"] == "Connected vehicle security platform"
    assert project["status"] == "active"
    assert "owner_id" not in project

    project_list = client.get("/v1/projects", headers=headers)
    assert project_list.status_code == 200
    assert project_list.json() == [project]

    detail = client.get(f"/v1/projects/{project['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json() == project

    connection = connect_database()
    try:
        audit_count = connection.execute(
            "SELECT COUNT(*) FROM project_audit_events WHERE entity_id = ?",
            (project["id"],),
        ).fetchone()[0]
        assert audit_count == 1
        with pytest.raises(sqlite3.IntegrityError, match="append_only"):
            connection.execute(
                "DELETE FROM project_audit_events WHERE entity_id = ?",
                (project["id"],),
            )
        connection.rollback()
    finally:
        connection.close()


def test_project_api_rejects_caller_supplied_owner_fields(monkeypatch, tmp_path):
    headers = _create_owner_session(monkeypatch, tmp_path)
    response = client.post(
        "/v1/projects",
        headers=headers,
        json={"name": "Handly", "owner_id": 999},
    )
    assert response.status_code == 422


def test_project_create_rejects_blank_name_and_missing_project(monkeypatch, tmp_path):
    headers = _create_owner_session(monkeypatch, tmp_path)
    invalid = client.post(
        "/v1/projects",
        headers=headers,
        json={"name": "   ", "description": "No name"},
    )
    assert invalid.status_code == 422

    missing = client.get("/v1/projects/not-a-real-project", headers=headers)
    assert missing.status_code == 404


def test_project_access_is_blocked_after_owner_logout(monkeypatch, tmp_path):
    headers = _create_owner_session(monkeypatch, tmp_path)
    created = client.post(
        "/v1/projects",
        headers=headers,
        json={"name": "CareLink Africa", "description": ""},
    )
    assert created.status_code == 201

    logout = client.post("/v1/auth/logout", headers=headers)
    assert logout.status_code == 200

    denied = client.get("/v1/projects", headers=headers)
    assert denied.status_code == 401

