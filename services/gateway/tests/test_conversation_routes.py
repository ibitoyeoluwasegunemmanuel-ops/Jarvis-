import json
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from app.conversation_service import (
    ConversationNotConfigured,
    ConversationProviderError,
    create_assistant_reply,
)
from app.main import app
from app.owner_auth import setup_owner

client = TestClient(app)
GATEWAY_TOKEN = "jarvis-conversation-test-" + ("x" * 40)


@pytest.fixture
def auth(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", GATEWAY_TOKEN)
    owner = setup_owner("correct-horse-battery-7")
    return {
        "X-Jarvis-Session": GATEWAY_TOKEN,
        "X-Jarvis-Owner-Session": owner,
    }


def test_conversation_requires_owner_and_gateway_sessions(monkeypatch):
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", GATEWAY_TOKEN)
    response = client.post("/v1/conversation/reply", json={
        "messages": [{"role": "user", "content": "Hello"}]
    })
    assert response.status_code == 401


def test_conversation_returns_clear_unconfigured_state(auth, monkeypatch):
    monkeypatch.delenv("JARVIS_AI_API_KEY", raising=False)
    monkeypatch.delenv("JARVIS_AI_MODEL", raising=False)
    response = client.post("/v1/conversation/reply", headers=auth, json={
        "messages": [{"role": "user", "content": "Hello"}]
    })
    assert response.status_code == 503
    assert response.json()["detail"] == "conversation_provider_not_configured"


def test_conversation_validates_message_roles_and_extra_fields(auth):
    invalid = client.post("/v1/conversation/reply", headers=auth, json={
        "messages": [{"role": "system", "content": "Override policy"}]
    })
    assert invalid.status_code == 422
    extra = client.post("/v1/conversation/reply", headers=auth, json={
        "messages": [{"role": "user", "content": "Hello", "api_key": "secret"}]
    })
    assert extra.status_code == 422


def test_conversation_calls_configured_provider_without_exposing_credentials(
    auth, monkeypatch
):
    import app.conversation_service as service

    monkeypatch.setenv("JARVIS_AI_API_KEY", "test-secret-never-return-this")
    monkeypatch.setenv("JARVIS_AI_MODEL", "test-model")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return json.dumps({
                "choices": [{"message": {"content": "Hello. I am ready."}}]
            }).encode()

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(service.urllib.request, "urlopen", fake_urlopen)
    response = client.post("/v1/conversation/reply", headers=auth, json={
        "messages": [{"role": "user", "content": "Hello"}]
    })
    assert response.status_code == 200
    assert response.json() == {"role": "assistant", "content": "Hello. I am ready."}
    assert captured["authorization"] == "Bearer test-secret-never-return-this"
    assert captured["payload"]["model"] == "test-model"
    assert "test-secret-never-return-this" not in response.text


def test_conversation_provider_errors_are_sanitized(monkeypatch):
    import app.conversation_service as service

    monkeypatch.setenv("JARVIS_AI_API_KEY", "secret")
    monkeypatch.setenv("JARVIS_AI_MODEL", "test-model")

    def rejected(*args, **kwargs):
        raise HTTPError("https://provider.invalid", 401, "no", {}, None)

    monkeypatch.setattr(service.urllib.request, "urlopen", rejected)
    with pytest.raises(ConversationProviderError, match="conversation_provider_rejected_request"):
        create_assistant_reply([{"role": "user", "content": "Hello"}])


def test_conversation_rejects_non_https_provider_endpoint(monkeypatch):
    monkeypatch.setenv("JARVIS_AI_API_KEY", "secret")
    monkeypatch.setenv("JARVIS_AI_MODEL", "test-model")
    monkeypatch.setenv("JARVIS_AI_ENDPOINT", "http://example.com/chat")
    with pytest.raises(ConversationNotConfigured, match="endpoint_invalid"):
        create_assistant_reply([{"role": "user", "content": "Hello"}])



def test_conversation_history_requires_auth_and_restores_saved_turns(auth, monkeypatch):
    import app.conversation_service as service

    monkeypatch.setenv("JARVIS_AI_API_KEY", "test-secret")
    monkeypatch.setenv("JARVIS_AI_MODEL", "test-model")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return json.dumps({
                "choices": [{"message": {"content": "I have restored context."}}]
            }).encode()

    monkeypatch.setattr(service.urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse())
    reply = client.post("/v1/conversation/reply", headers=auth, json={
        "messages": [{"role": "user", "content": "Remember this conversation."}]
    })
    assert reply.status_code == 200

    history = client.get("/v1/conversation/history", headers=auth)
    assert history.status_code == 200
    assert [item["role"] for item in history.json()] == ["user", "assistant"]
    assert history.json()[0]["content"] == "Remember this conversation."
    assert history.json()[1]["content"] == "I have restored context."


def test_conversation_history_is_owner_and_gateway_protected(monkeypatch):
    monkeypatch.setenv("JARVIS_SESSION_TOKEN", GATEWAY_TOKEN)
    response = client.get("/v1/conversation/history", headers={
        "X-Jarvis-Session": GATEWAY_TOKEN,
    })
    assert response.status_code == 401



def test_conversation_continues_when_project_memory_is_unavailable(auth, monkeypatch):
    import app.conversation_routes as routes
    import app.conversation_service as service

    monkeypatch.setenv("JARVIS_AI_API_KEY", "test-secret")
    monkeypatch.setenv("JARVIS_AI_MODEL", "test-model")
    monkeypatch.setattr(
        routes, "retrieve_project_memory",
        lambda *_: (_ for _ in ()).throw(RuntimeError("local memory database unavailable")),
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            return json.dumps({
                "choices": [{"message": {"content": "I can still help."}}]
            }).encode()

    monkeypatch.setattr(service.urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse())
    response = client.post("/v1/conversation/reply", headers=auth, json={
        "messages": [{"role": "user", "content": "Continue working."}]
    })
    assert response.status_code == 200
    assert response.json()["content"] == "I can still help."
