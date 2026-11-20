"""Authenticated JARVIS conversation endpoint."""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.approval_routes import _require_owner
from app.conversation_service import (
    ConversationNotConfigured,
    ConversationProviderError,
    create_assistant_reply,
)

router = APIRouter(prefix="/v1/conversation", tags=["conversation"])


class ConversationMessage(BaseModel):
    model_config = {"extra": "forbid"}

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)


class ConversationRequest(BaseModel):
    model_config = {"extra": "forbid"}

    messages: list[ConversationMessage] = Field(min_length=1, max_length=20)


@router.post("/reply", dependencies=[Depends(_require_owner)])
def conversation_reply(payload: ConversationRequest) -> dict[str, str]:
    """Generate one assistant reply for the authenticated local owner."""
    try:
        return create_assistant_reply(
            [message.model_dump() for message in payload.messages]
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except ConversationNotConfigured as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ConversationProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
