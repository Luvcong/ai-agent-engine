import uuid
from pydantic import BaseModel
from typing import List, Dict, Any

class DummyMessage(BaseModel):
    tool_calls: List[Dict[str, Any]]

class Agent:
    """
    agent_service.py의 astream 호출을 에뮬레이트하는 에코(Echo) 에이전트입니다.
    """
    async def astream(self, input_data: dict, config: dict = None, stream_mode: str = "updates"):
        # 입력된 메시지 내용 추출
        messages = input_data.get("messages", [])
        user_content = ""
        if messages:
             # HumanMessage 객체의 content 속성을 가져옵니다.
             user_content = getattr(messages[-1], "content", str(messages[-1]))
        
        # agent_service.py가 기대하는 ChatResponse tool_call 형태의 모의 객체 생성
        dummy_message = DummyMessage(
            tool_calls=[
                {
                    "name": "ChatResponse",
                    "args": {
                        "message_id": str(uuid.uuid4()),
                        "content": f"Echo: {user_content}",
                        "metadata": {}
                    }
                }
            ]
        )
        
        # 'model' step의 결과 구조로 모의 반환
        yield {
            "model": {
                "messages": [dummy_message]
            }
        }