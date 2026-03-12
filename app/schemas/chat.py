from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ChatRequest(BaseModel):
    thread_id: UUID
    message: str


class ResponseMetadata(BaseModel):
    tool_name: str | None = None
    query: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    message_id: str
    content: str
    metadata: ResponseMetadata

__all__ = ["ChatRequest", "ChatResponse", "ResponseMetadata"]
