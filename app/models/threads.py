from typing import List, Literal, Optional, Union
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime

from app.models.chat import ResponseMetadata
from typing import TypeVar, Generic


T = TypeVar("T")

class RootBaseModel(BaseModel, Generic[T]):
    response: T


class UserMessageData(BaseModel):
    message_id: UUID
    role: Literal["user"] = "user"
    content: str
    is_favorited: bool = False
    created_at: datetime


class AIMessageData(BaseModel):
    message_id: UUID
    role: Literal["assistant"] = "assistant"
    content: str
    metadata: Optional[ResponseMetadata] = {}
    created_at: datetime



class ThreadDataResponse(BaseModel):
    thread_id: UUID
    title: str
    messages: List[Union[UserMessageData, AIMessageData]]
