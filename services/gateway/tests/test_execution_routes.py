from fastapi.testclient import TestClient

from app.main import app
from app.approval_store import decide_approval, request_approval
from app.owner_auth import setup_owner
from app.workspace_store import create_project, list_project_tasks


def test_execution_derives_owner_identity_and_executes_exact_approved_task(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-token-123456789")
    owner_token = setup_owner("correct-horse-battery-7")
    project = create_project("Execution API Test")
    arguments = {
        "project_id": project["id"],
        "title": "Verify approved execution",
        "description": "Created through the trusted owner execution route.",
    }
    approval = request_approval(
        project["id"], "project.task.create", arguments,
        requester="owner", ttl_seconds=300,
    )
    decide_approval(approval["id"], True)
    client = TestClient(app)
    headers = {
        "X-Jarvis-Session": "test-gateway-session-token-123456789",
        "X-Jarvis-Owner-Session": owner_token,
    }

    response = client.post("/v1/execution/approved", headers=headers, json={
        "approval_id": approval["id"],
        "nonce": approval["nonce"],
        "action": "project.task.create",
        "arguments": arguments,
    })

    assert response.status_code == 200
    assert response.json()["status"] == "executed"
    assert response.json()["result"]["title"] == arguments["title"]
    assert len(list_project_tasks(project["id"])) == 1

    replay = client.post("/v1/execution/approved", headers=headers, json={
        "approval_id": approval["id"],
        "nonce": approval["nonce"],
        "action": "project.task.create",
        "arguments": arguments,
    })
    assert replay.status_code == 409
    assert len(list_project_tasks(project["id"])) == 1


def test_execution_rejects_caller_supplied_identity_and_scopes(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", "test-gateway-session-token-123456789")
    owner_token = setup_owner("correct-horse-battery-7")
    project = create_project("Execution Identity Test")
    client = TestClient(app)
    headers = {
        "X-Jarvis-Session": "test-gateway-session-token-123456789",
        "X-Jarvis-Owner-Session": owner_token,
    }
    response = client.post("/v1/execution/approved", headers=headers, json={
        "approval_id": "approval-id",
        "nonce": "nonce",
        "action": "project.task.create",
        "arguments": {"project_id": project["id"], "title": "No spoofing"},
        "actor_id": "agent:orchestrator",
        "granted_scopes": ["projects:write"],
    })
    assert response.status_code == 422
