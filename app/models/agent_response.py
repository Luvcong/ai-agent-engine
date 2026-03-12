from typing import Any

from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    message_id: str = Field(description="Assistant message UUID")
    content: str = Field(description="Final answer shown to the user")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data returned from tool calls",
    )
