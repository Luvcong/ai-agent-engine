from typing import Dict, Optional
from pydantic import BaseModel
from uuid import UUID


class ChatRequest(BaseModel):
    thread_id: UUID
    message: str


class ResponseMetadata(BaseModel):
    pass


class ChatResponse(BaseModel):
    message_id: str
    content: str
    metadata: ResponseMetadata
