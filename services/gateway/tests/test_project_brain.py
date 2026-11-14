import sqlite3

import pytest

from app.owner_auth import setup_owner
from app.project_brain import (
    create_project_memory,
    create_project_risk,
    list_project_memory,
    list_project_risks,
    update_project_risk_status,
)
from app.workspace_store import create_project, list_project_activity


@pytest.fixture
def project(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    setup_owner("correct-horse-battery-7")
    return create_project("Project Brain Test")["id"]


def test_risk_register_is_owner_scoped_and_audited(project):
    risk = create_project_risk(
        project, "Data loss", "Backups are not verified", "critical", "Test restore weekly"
    )
    assert risk["status"] == "open"
    assert list_project_risks(project)[0]["severity"] == "critical"

    updated = update_project_risk_status(risk["id"], "mitigated")
    assert updated["status"] == "mitigated"
    events = list_project_activity(project)
    assert {event["event_type"] for event in events} >= {
        "risk.created", "risk.status_changed"
    }


def test_risk_validation_rejects_unknown_severity(project):
    with pytest.raises(ValueError, match="risk_severity_invalid"):
        create_project_risk(project, "Risk", "", "catastrophic")


def test_project_memory_is_append_only_and_source_attributed(project, monkeypatch, tmp_path):
    item = create_project_memory(
        project, "fact", "The MVP is local-first", "decision-log#12", 0.95
    )
    assert item["source_ref"] == "decision-log#12"
    assert list_project_memory(project)[0]["confidence"] == 0.95

    from app.owner_auth import connect_database

    connection = connect_database()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append_only"):
            connection.execute(
                "UPDATE project_memory SET content = 'changed' WHERE id = ?",
                (item["id"],),
            )
        connection.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append_only"):
            connection.execute("DELETE FROM project_memory WHERE id = ?", (item["id"],))
        connection.rollback()
    finally:
        connection.close()

    assert "memory.recorded" in {
        event["event_type"] for event in list_project_activity(project)
    }


def test_memory_confidence_and_category_are_validated(project):
    with pytest.raises(ValueError, match="memory_confidence_invalid"):
        create_project_memory(project, "fact", "A fact", confidence=1.5)
    with pytest.raises(ValueError, match="memory_category_invalid"):
        create_project_memory(project, "secret", "A fact")
