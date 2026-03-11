from dataclasses import dataclass
from typing import Optional

# We use a dataclass here, but Pydantic models are also supported.
@dataclass
class ResponseFormat:
    """Response schema for the agent."""
    # A punny response (always required)
    punny_response: str    # Agent가 생성하는 답변 스타일
    
    # Any interesting information about the weather if available
    weather_conditions: Optional[str]   # Tool에서 받은 실제 날씨 정보