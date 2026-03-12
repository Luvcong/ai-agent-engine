import uuid

from app.orchestration.streaming import (
    build_done_event,
    build_model_event,
    serialize_sse_event,
)
from app.utils.logger import custom_logger
from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest
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
        "message": "타이레놀이 어떤 약인지 알려줘"
    }
    ```
    """
    custom_logger.info(f"API Request: {request}")
    try:
        thread_id = getattr(request, "thread_id", uuid.uuid4())
        
        async def event_generator():
            try:
                yield serialize_sse_event(build_model_event(["Planning"]))
                
                # agentService 생성
                agent_service = AgentService()

                async for chunk in agent_service.process_query(
                    user_messages=request.message,
                    thread_id=thread_id
                ):
                    yield serialize_sse_event(chunk)
            except Exception as e:
                # 스트리밍 중 예외 발생 시 에러 메시지를 스트리밍으로 전송
                error_response = build_done_event(
                    message_id=str(uuid.uuid4()),
                    content="요청 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                    metadata={},
                    error=str(e),
                )
                yield serialize_sse_event(error_response)
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
