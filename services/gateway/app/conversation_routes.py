"""Authenticated JARVIS conversation endpoint."""
from typing import Literal
import logging

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

router = APIRouter(prefix="/v1/conversation", tags=["conversation"])
logger = logging.getLogger(__name__)


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
        reply = create_assistant_reply(
            [message.model_dump() for message in payload.messages],
            memory_context=memory_context,
        )
        save_conversation_turn(payload.messages[-1].content, reply["content"])
        return reply
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ConversationNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ConversationProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
