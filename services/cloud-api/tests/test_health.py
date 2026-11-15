from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_is_public_and_does_not_require_cloud_credentials():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "jarvis-cloud-api"


def test_private_routes_require_bearer_token():
    response = client.get("/v1/devices", params={"workspace_id": "00000000-0000-0000-0000-000000000001"})
    assert response.status_code == 401
    assert response.json()["detail"] == "bearer_token_required"


def test_workspace_list_requires_bearer_token():
    response = client.get("/v1/workspaces")
    assert response.status_code == 401
    assert response.json()["detail"] == "bearer_token_required"


def test_device_heartbeat_requires_bearer_token():
    response = client.post(
        "/v1/devices/00000000-0000-0000-0000-000000000001/heartbeat"
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "bearer_token_required"
