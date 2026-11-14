import pytest

from app.approval_store import list_project_approvals, request_approval
from app.dispatcher import DispatchError, dispatch_approved_action
from app.owner_auth import setup_owner
from app.policy import ActorContext
from app.workspace_store import create_project, list_project_activity, list_project_tasks


@pytest.fixture
def workspace(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")
    project = create_project("Dispatcher Test")
    return project["id"]


def _approved(project_id, action, arguments):
    created = request_approval(
        project_id, action, arguments, requester="agent:orchestrator", ttl_seconds=300
    )
    decision = decide_approval(created["id"], True)
    assert decision["status"] == "approved"
    return created


def test_dispatch_executes_only_exact_approved_allowlisted_action(workspace):
    arguments = {
        "project_id": workspace,
        "title": "Verify worker onboarding",
        "description": "Run the customer and worker journey checks.",
    }
    approval = _approved(workspace, "project.task.create", arguments)
    actor = ActorContext(
        "agent:orchestrator", workspace, frozenset({"projects:write"})
    )

    result = dispatch_approved_action(
        actor, approval["id"], approval["nonce"], "project.task.create", arguments
    )

    assert result["status"] == "executed"
    assert result["result"]["title"] == "Verify worker onboarding"
    assert len(list_project_tasks(workspace)) == 1
    execution_events = [event for event in list_project_activity(workspace) if event["entity_type"] == "action_execution"]
    assert {event["event_type"] for event in execution_events} == {"action_execution.started", "action_execution.succeeded"}
    assert all(approval["id"] in event["entity_id"] for event in execution_events)
    with pytest.raises(DispatchError, match="approval_not_approved_or_already_used"):
        dispatch_approved_action(
            actor, approval["id"], approval["nonce"], "project.task.create", arguments
        )


def test_dispatch_rejects_unallowlisted_action_without_consuming_approval(workspace):
    arguments = {"project_id": workspace, "url": "https://example.com"}
    approval = _approved(workspace, "browser.navigate", arguments)
    actor = ActorContext("agent:orchestrator", workspace, frozenset({"projects:write"}))

    with pytest.raises(DispatchError, match="not_allowlisted"):
        dispatch_approved_action(
            actor, approval["id"], approval["nonce"], "browser.navigate", arguments
        )

    assert list_project_approvals(workspace)[0]["status"] == "approved"


def test_dispatch_rechecks_scope_and_workspace_before_consumption(workspace):
    arguments = {"project_id": workspace, "title": "Protected task"}
    approval = _approved(workspace, "project.task.create", arguments)

    wrong_scope = ActorContext("agent:orchestrator", workspace, frozenset())
    with pytest.raises(DispatchError, match="policy_denied"):
        dispatch_approved_action(
            wrong_scope, approval["id"], approval["nonce"], "project.task.create", arguments
        )

    wrong_workspace = ActorContext(
        "agent:orchestrator", "another-project", frozenset({"projects:write"})
    )
    with pytest.raises(DispatchError, match="workspace_mismatch"):
        dispatch_approved_action(
            wrong_workspace, approval["id"], approval["nonce"], "project.task.create", arguments
        )

    assert len(list_project_tasks(workspace)) == 0


def test_dispatch_rejects_tampered_arguments_and_wrong_nonce(workspace):
    arguments = {"project_id": workspace, "title": "Original task"}
    approval = _approved(workspace, "project.task.create", arguments)
    actor = ActorContext("agent:orchestrator", workspace, frozenset({"projects:write"}))

    with pytest.raises(DispatchError, match="binding_mismatch"):
        dispatch_approved_action(
            actor, approval["id"], approval["nonce"], "project.task.create",
            {**arguments, "title": "Tampered task"},
        )
    with pytest.raises(DispatchError, match="binding_mismatch"):
        dispatch_approved_action(
            actor, approval["id"], "wrong-nonce", "project.task.create", arguments
        )
    assert len(list_project_tasks(workspace)) == 0


def test_dispatch_rejects_approval_from_different_project_before_consumption(
    workspace, monkeypatch, tmp_path
):
    from app.approval_store import decide_approval, request_approval, list_project_approvals

    other_project = create_project("Different Workspace")
    arguments = {"project_id": other_project["id"], "title": "Wrong project task"}
    created = request_approval(
        workspace, "project.task.create", arguments,
        requester="agent:orchestrator", ttl_seconds=300,
    )
    decide_approval(created["id"], True)
    actor = ActorContext(
        "agent:orchestrator", other_project["id"], frozenset({"projects:write"})
    )

    with pytest.raises(DispatchError, match="approval_project_binding_mismatch"):
        dispatch_approved_action(
            actor, created["id"], created["nonce"], "project.task.create", arguments
        )

    assert list_project_approvals(workspace)[0]["status"] == "approved"
    assert list_project_tasks(other_project["id"]) == []
