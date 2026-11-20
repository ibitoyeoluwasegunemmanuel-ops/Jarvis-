"""Authenticated JARVIS conversation endpoint."""
from typing import Literal
import logging
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.approval_routes import _require_owner
from app.conversation_service import (
    ConversationNotConfigured,
    ConversationProviderError,
    create_assistant_reply,
)
from app.conversation_store import list_conversation_history, save_conversation_turn
from app.conversation_memory import retrieve_project_memory
from app.monitoring_providers import github_repository

router = APIRouter(prefix="/v1/conversation", tags=["conversation"])
logger = logging.getLogger(__name__)
_GITHUB_QUERY_TERMS = ("github", "repository", "repo", "branch", "commit", "pull request", "pull-request", "workflow", "build", "actions")


def _github_context_for_query(query: str) -> str | None:
    lowered = query.lower()
    if not any(term in lowered for term in _GITHUB_QUERY_TERMS) and not re.search(r"\\b(ci|pr)\\b", lowered):
        return None
    try:
        snapshot = github_repository()
    except Exception:
        logger.exception("conversation_github_context_failed")
        return None
    if snapshot.get("status") != "connected":
        return None
    lines = [
        f"Repository: {snapshot.get('repository', 'unknown')}",
        f"Default branch: {snapshot.get('default_branch', 'unknown')}",
        "Branches: " + ", ".join(
            str(item.get("name", "")) + (" (protected)" if item.get("protected") else "")
            for item in snapshot.get("branches", [])[:10]
        ),
        "Recent commits: " + "; ".join(
            f"{item.get('sha', '')}: {item.get('message', '')}"
            for item in snapshot.get("recent_commits", [])[:5]
        ),
        "Open pull requests: " + "; ".join(
            f"#{item.get('number', '')} {item.get('title', '')} ({item.get('head', '')} -> {item.get('base', '')})"
            for item in snapshot.get("open_pull_requests", [])[:10]
        ),
        "Recent workflow runs: " + "; ".join(
            f"{item.get('name', '')} on {item.get('branch', '')}: {item.get('status', '')}/{item.get('conclusion', '') or 'pending'}"
            for item in snapshot.get("workflow_runs", [])[:10]
        ),
    ]
    return "\\n".join(lines)[:6_000]


class ConversationMessage(BaseModel):
    model_config = {"extra": "forbid"}

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)


class ConversationRequest(BaseModel):
    model_config = {"extra": "forbid"}

    messages: list[ConversationMessage] = Field(min_length=1, max_length=20)


@router.get("/history", dependencies=[Depends(_require_owner)])
def conversation_history() -> list[dict[str, object]]:
    """Return the recent private conversation for the signed-in local owner."""
    return list_conversation_history()


@router.post("/reply", dependencies=[Depends(_require_owner)])
def conversation_reply(payload: ConversationRequest) -> dict[str, str]:
    """Generate one assistant reply for the authenticated local owner."""
    try:
        latest_user_message = payload.messages[-1].content
        try:
            memory_context = retrieve_project_memory(latest_user_message)
        except Exception:
            # Project memory is optional context; a local DB issue must not take chat offline.
            logger.exception("conversation_memory_retrieval_failed")
            memory_context = []
        github_context = _github_context_for_query(latest_user_message)
        reply = create_assistant_reply(
            [message.model_dump() for message in payload.messages],
            memory_context=memory_context,
            github_context=github_context,
        )
        save_conversation_turn(payload.messages[-1].content, reply["content"])
        return reply
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ConversationNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ConversationProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
