import uuid

from app.utils.logger import custom_logger
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest
from app.services.agent_service import AgentService
from fastapi.responses import StreamingResponse

chat_router = APIRouter()


@chat_router.post("/chat")
async def post_chat(request: ChatRequest):
    """
    자연어 쿼리를 에이전트가 처리합니다.

    ## 실제 테스트용 Request json
    ```json
    {
        "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "message": "안녕하세요, 오늘 날씨가 어때요?"
    }
    ```
    """
    custom_logger.info(f"API Request: {request}")
    try:
        # agent_service = AgentService()
        thread_id = getattr(request, "thread_id", uuid.uuid4())
        
        async def event_generator():
            try:
                yield f'data: {{"step": "model", "tool_calls": ["Planning"]}}\n\n'
                agent_service = AgentService()
                async for chunk in agent_service.process_query(
                    user_messages=request.message,
                    thread_id=thread_id
                ):
                    yield f"data: {chunk}\n\n"
            except Exception as e:
                # 스트리밍 중 예외 발생 시 에러 메시지를 스트리밍으로 전송
                import json
                from datetime import datetime
                error_response = {
                    "step": "done",
                    "message_id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": "요청 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                    "metadata": {},
                    "created_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                custom_logger.error(f"Error in event_generator: {e}")
                import traceback
                custom_logger.error(traceback.format_exc())
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        # 스트리밍 시작 전 예외만 HTTPException으로 처리
        custom_logger.error(f"Error in /chat (before streaming): {e}")
        import traceback
        custom_logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

