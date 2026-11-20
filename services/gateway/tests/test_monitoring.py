# isort: skip_file
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.monitoring_store import (
    acknowledge_alert, create_alert, list_alerts, list_connectors,
    register_connector, update_connector_health,
)
from app.owner_auth import setup_owner


@pytest.fixture
def owner_client(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")
    token = "x" * 48
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", token)
    client = TestClient(app)
    return client, token


def test_connector_registry_is_owner_authenticated(owner_client):
    client, process_token = owner_client
    denied = client.get("/v1/monitoring/connectors")
    assert denied.status_code == 401
    result = client.post(
        "/v1/monitoring/connectors",
        headers={"X-Jarvis-Session": process_token, "X-Jarvis-Owner-Session": "bad"},
        json={"workspace": "WorldScope News", "provider": "vercel",
              "display_name": "WorldScope Vercel", "scopes": ["deployments:read"]},
    )
    assert result.status_code == 401


def test_monitoring_api_requires_gateway_and_owner_sessions(owner_client):
    client, process_token = owner_client
    login = client.post(
        "/v1/auth/login",
        headers={"X-Jarvis-Session": process_token},
        json={"password": "correct-horse-battery-7"},
    )
    assert login.status_code == 200
    owner_token = login.json()["owner_session_token"]
    headers = {
        "X-Jarvis-Session": process_token,
        "X-Jarvis-Owner-Session": owner_token,
    }
    created = client.post(
        "/v1/monitoring/connectors",
        headers=headers,
        json={"workspace": "WorldScope News", "provider": "vercel",
              "display_name": "WorldScope Vercel", "scopes": ["deployments:read"]},
    )
    assert created.status_code == 201
    assert created.json()["status"] == "disconnected"
    listed = client.get("/v1/monitoring/connectors", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == created.json()["id"]


def test_connector_registration_is_read_only_and_health_tracked(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")
    connector = register_connector(
        "WorldScope News", "vercel", "WorldScope Vercel", ["deployments:read"]
    )
    assert connector["status"] == "disconnected"
    healthy = update_connector_health(connector["id"], "healthy", "Read-only check passed")
    assert healthy["last_success_at"] is not None
    assert healthy["scopes"] == ["deployments:read"]
    assert list_connectors()[0]["id"] == connector["id"]


def test_connector_rejects_write_or_admin_scope(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")
    with pytest.raises(ValueError, match="monitoring_connectors_read_only"):
        register_connector("HANDLY", "supabase", "Production DB", ["database:write"])


def test_alerts_deduplicate_and_acknowledge(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")
    first = create_alert("WorldScope News", "critical", "Publishing failed", "Job 42 failed")
    second = create_alert("WorldScope News", "critical", "Publishing failed", "Job 42 still failing")
    assert first["id"] == second["id"]
    assert len(list_alerts("open")) == 1
    ack = acknowledge_alert(first["id"])
    assert ack["status"] == "acknowledged"
    assert ack["acknowledged_at"] is not None


def test_provider_overview_uses_fixed_read_only_adapters(monkeypatch):
    from app import monitoring_providers

    monkeypatch.setenv("VERCEL_TOKEN", "vercel-test-token")
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "supabase-test-token")
    monkeypatch.setenv("GITHUB_TOKEN", "github-test-token")
    monkeypatch.setenv("JARVIS_GITHUB_REPOSITORY", "ibitoyeoluwasegunemmanuel-ops/Jarvis-")
    requested = []

    def fake_get_json(url, token):
        requested.append((url, token))
        if "vercel.com" in url:
            return {"deployments": [{"uid": "d1", "name": "worldscope",
                                     "url": "example.vercel.app", "state": "READY"}]}
        if "api.supabase.com" in url:
            return [{"ref": "abcdefghijklmnopqrst", "name": "carelink",
                     "region": "eu-west-1", "status": "ACTIVE_HEALTHY"}]
        if url.endswith("/branches?per_page=10"):
            return [{"name": "main", "protected": True}]
        if url.endswith("/commits?per_page=5"):
            return [{"sha": "1234567890abcdef", "commit": {"message": "Initial commit",
                     "author": {"name": "CEO Global", "date": "2026-11-20T12:00:00Z"}},
                     "html_url": "https://github.com/example/repo/commit/123"}]
        if url.endswith("/pulls?state=open&per_page=10"):
            return [{"number": 1, "title": "Foundation", "state": "open",
                     "html_url": "https://github.com/example/repo/pull/1",
                     "head": {"ref": "feature"}, "base": {"ref": "main"}}]
        return {"full_name": "example/repo", "private": False,
                "default_branch": "main", "updated_at": "2026-11-20T12:00:00Z",
                "html_url": "https://github.com/example/repo"}

    monkeypatch.setattr(monitoring_providers, "_get_json", fake_get_json)
    result = monitoring_providers.provider_overview()
    assert result["read_only"] is True
    assert [item["status"] for item in result["providers"]] == [
        "connected", "connected", "connected"
    ]
    github = result["providers"][2]
    assert github["default_branch"] == "main"
    assert github["recent_commits"][0]["message"] == "Initial commit"
    assert github["open_pull_requests"][0]["number"] == 1
    assert len(requested) == 6
    assert all(url.startswith("https://api.") for url, _ in requested)
    assert {token for _, token in requested} == {
        "vercel-test-token", "supabase-test-token", "github-test-token"
    }


def test_provider_overview_reports_missing_tokens_without_network(monkeypatch):
    from app import monitoring_providers

    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("JARVIS_GITHUB_REPOSITORY", "invalid")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(
        monitoring_providers, "_get_json",
        lambda *_: (_ for _ in ()).throw(AssertionError("network must not be called")),
    )
    result = monitoring_providers.provider_overview()
    assert [item["status"] for item in result["providers"]] == [
        "not_configured", "not_configured", "unavailable"
    ]
