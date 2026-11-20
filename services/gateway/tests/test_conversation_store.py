import pytest

from app.conversation_store import list_conversation_history, save_conversation_turn
from app.owner_auth import setup_owner


@pytest.fixture
def local_owner(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")


def test_conversation_turns_persist_in_order(local_owner):
    save_conversation_turn("First user message", "First assistant reply")
    save_conversation_turn("Second user message", "Second assistant reply")

    history = list_conversation_history()

    assert [item["role"] for item in history] == [
        "user", "assistant", "user", "assistant"
    ]
    assert [item["content"] for item in history] == [
        "First user message",
        "First assistant reply",
        "Second user message",
        "Second assistant reply",
    ]


def test_conversation_history_limit_is_validated(local_owner):
    with pytest.raises(ValueError, match="conversation_history_limit_invalid"):
        list_conversation_history(0)
