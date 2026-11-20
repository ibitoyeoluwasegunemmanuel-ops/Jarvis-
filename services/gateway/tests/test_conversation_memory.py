import pytest

from app.owner_auth import setup_owner
from app.project_brain import create_project_memory
from app.conversation_memory import retrieve_project_memory
from app.workspace_store import create_project


@pytest.fixture
def saved_memory(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")
    project = create_project("HANDLY marketplace")["id"]
    create_project_memory(
        project, "decision", "HANDLY will use state and LGA based worker matching."
    )
    create_project_memory(
        project, "fact", "The mobile app uses Flutter."
    )
    return project


def test_retrieval_returns_relevant_owner_project_memory(saved_memory):
    results = retrieve_project_memory("How will HANDLY match workers?", limit=5)
    assert results
    assert results[0]["project_name"] == "HANDLY marketplace"
    assert "state and LGA" in results[0]["content"]


def test_retrieval_ignores_unrelated_memory(saved_memory):
    assert retrieve_project_memory("Tell me about a completely unrelated recipe") == []


def test_retrieval_limit_is_bounded():
    with pytest.raises(ValueError, match="memory_retrieval_limit_invalid"):
        retrieve_project_memory("HANDLY", limit=99)
