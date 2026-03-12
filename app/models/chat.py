from typing import Any
from pydantic import BaseModel
from uuid import UUID


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
