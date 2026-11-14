import pytest

from app.approval_store import (
    ApprovalError,
    consume_approval,
    decide_approval,
    list_project_approvals,
    request_approval,
)
from app.owner_auth import setup_owner
from app.workspace_store import create_project


@pytest.fixture
def project(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")
    return create_project("Approval Test")["id"]


def test_approval_binds_exact_action_arguments_and_is_single_use(project):
    requested = request_approval(
        project, "browser.navigate", {"url": "https://example.com", "wait": 2}
    )
    assert requested["status"] == "pending"
    assert decide_approval(requested["id"], True)["status"] == "approved"

    with pytest.raises(ApprovalError, match="binding_mismatch"):
        consume_approval(
            requested["id"], "browser.navigate",
            {"url": "https://example.com/other", "wait": 2}, requested["nonce"],
        )

    consumed = consume_approval(
        requested["id"], "browser.navigate",
        {"wait": 2, "url": "https://example.com"}, requested["nonce"],
    )
    assert consumed["arguments"]["url"] == "https://example.com"
    with pytest.raises(ApprovalError, match="not_approved_or_already_used"):
        consume_approval(
            requested["id"], "browser.navigate",
            {"url": "https://example.com", "wait": 2}, requested["nonce"],
        )


def test_approval_rejects_wrong_action_and_nonce(project):
    requested = request_approval(project, "file.read", {"path": "reports/summary.md"})
    decide_approval(requested["id"], True)
    with pytest.raises(ApprovalError, match="binding_mismatch"):
        consume_approval(requested["id"], "file.delete", {"path": "reports/summary.md"}, requested["nonce"])
    with pytest.raises(ApprovalError, match="binding_mismatch"):
        consume_approval(requested["id"], "file.read", {"path": "reports/summary.md"}, "wrong-nonce")


def test_denied_approval_cannot_be_consumed(project):
    requested = request_approval(project, "deployment.publish", {"environment": "production"})
    decide_approval(requested["id"], False)
    with pytest.raises(ApprovalError, match="not_approved_or_already_used"):
        consume_approval(
            requested["id"], "deployment.publish",
            {"environment": "production"}, requested["nonce"],
        )


def test_approval_validation_rejects_invalid_ttl_and_non_json(project):
    with pytest.raises(ApprovalError, match="ttl_invalid"):
        request_approval(project, "browser.navigate", {}, ttl_seconds=0)
    with pytest.raises(ApprovalError, match="arguments_invalid"):
        request_approval(project, "browser.navigate", {"bad": object()})


def test_approval_history_lists_without_exposing_nonce(project):
    requested = request_approval(project, "browser.navigate", {"url": "https://example.com"})
    items = list_project_approvals(project)
    assert items is not None
    assert len(items) == 1
    assert items[0]["id"] == requested["id"]
    assert items[0]["status"] == "pending"
    assert "nonce" not in items[0]
    assert items[0]["arguments"] == {"url": "https://example.com"}
