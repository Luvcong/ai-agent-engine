import asyncio
import contextlib
from datetime import datetime
import json
import uuid

from app.core.config import settings
from app.observability.opik import create_opik_tracer
from app.utils.logger import log_execution, custom_logger

from langchain_core.messages import HumanMessage


class AgentService:
    # 스트리밍 중간 진행 상태를 전달하기 위한 큐를 준비한다.
    def __init__(self):
        self.progress_queue: asyncio.Queue = asyncio.Queue()

    # 현재 초기화된 의료 에이전트 인스턴스를 가져온다.
    def _get_agent(self):
        """공유 LangChain 에이전트를 반환합니다."""
        from app.agents.medical import get_medical_agent
        return get_medical_agent()

    # 최종 응답 본문에 섞여 들어온 metadata 텍스트를 제거해 사용자 응답만 남긴다.
    def _sanitize_final_content(self, content: str | None) -> str:
        if not content:
            return ""

        normalized = content.strip()
        metadata_marker = "\nmetadata:"
        lowered = normalized.lower()
        marker_index = lowered.find(metadata_marker)
        if marker_index != -1:
            normalized = normalized[:marker_index].rstrip()

        if normalized.lower().startswith("metadata:"):
            return ""
        return normalized

    # 실제 대화 로직
    @log_execution
    async def process_query(self, user_messages: str, thread_id: uuid.UUID):
        """LangChain Messages 형식의 쿼리를 처리하고 AIMessage 형식으로 반환합니다."""
        opik_tracer = None
        try:
            agent = self._get_agent()
            opik_tracer = create_opik_tracer(str(thread_id))

            custom_logger.info(f"사용자 메시지: {user_messages}")

            config = {
                "configurable": {"thread_id": str(thread_id)},
                "recursion_limit": settings.DEEPAGENT_RECURSION_LIMIT,
            }
            if opik_tracer is not None:
                config["callbacks"] = [opik_tracer]

            agent_stream = agent.astream(
                {"messages": [HumanMessage(content=user_messages)]},
                config=config,
                stream_mode="updates",
            )

            agent_iterator = agent_stream.__aiter__()
            agent_task = asyncio.create_task(agent_iterator.__anext__())
            progress_task = asyncio.create_task(self.progress_queue.get())

            while True:
                pending = {agent_task}
                if progress_task is not None:
                    pending.add(progress_task)

                done, _ = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

                if progress_task in done:
                    try:
                        progress_event = progress_task.result()
                        yield json.dumps(progress_event, ensure_ascii=False)
                        progress_task = asyncio.create_task(self.progress_queue.get())
                    except asyncio.CancelledError:
                        progress_task = None
                    except Exception as e:
                        # progress_task에서 예외 발생 시 로그만 남기고 계속 진행
                        custom_logger.error(f"Error in progress_task: {e}")
                        progress_task = None

                if agent_task in done:
                    try:
                        chunk = agent_task.result()
                    except StopAsyncIteration:
                        agent_task = None
                        break
                    except Exception as e:
                        # Task에서 발생한 예외 처리
                        custom_logger.error(f"Error in agent_task: {e}")
                        import traceback
                        custom_logger.error(traceback.format_exc())
                        agent_task = None
                        # 에러를 스트리밍으로 전송
                        error_response = {
                            "step": "done",
                            "message_id": str(uuid.uuid4()),
                            "role": "assistant",
                            "content": "처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                            "metadata": {},
                            "created_at": datetime.utcnow().isoformat(),
                            "error": str(e)
                        }
                        yield json.dumps(error_response, ensure_ascii=False)
                        break

                    custom_logger.info(f"에이전트 청크: {chunk}")
                    try:
                        for step, event in chunk.items():
                            # create_agent(..., stream_mode="updates")는 model/tools 단계별로
                            # 이벤트를 나눠 준다. 여기서는 프론트가 이해하기 쉬운 SSE 형태로 재가공한다.
                            if not event or not (step in ["model", "tools"]):
                                continue
                            messages = event.get("messages", [])
                            if len(messages) == 0:
                                continue
                            message = messages[0]
                            if step == "model":
                                tool_calls = message.tool_calls
                                if not tool_calls:
                                    continue
                                tool = tool_calls[0]
                                if tool.get("name") in {"AgentResponse", "ChatResponse"}:
                                    args = tool.get("args", {})
                                    metadata = args.get("metadata")
                                    custom_logger.info("========================================")
                                    custom_logger.info(args)
                                    sanitized_content = self._sanitize_final_content(
                                        args.get("content")
                                    )
                                    yield f'{{"step": "done", "message_id": {json.dumps(args.get("message_id"))}, "role": "assistant", "content": {json.dumps(sanitized_content, ensure_ascii=False)}, "metadata": {json.dumps(self._handle_metadata(metadata), ensure_ascii=False)}, "created_at": "{datetime.utcnow().isoformat()}"}}'
                                else:
                                    yield f'{{"step": "model", "tool_calls": {json.dumps([tool["name"] for tool in tool_calls])}}}'
                            if step == "tools":
                                yield f'{{"step": "tools", "name": {json.dumps(message.name)}, "content": {message.content}}}'
                    except Exception as e:
                        # 청크 처리 중 예외 발생
                        custom_logger.error(f"Error processing chunk: {e}")
                        import traceback
                        custom_logger.error(traceback.format_exc())
                        error_response = {
                            "step": "done",
                            "message_id": str(uuid.uuid4()),
                            "role": "assistant",
                            "content": "데이터 처리 중 오류가 발생했습니다.",
                            "metadata": {},
                            "created_at": datetime.utcnow().isoformat(),
                            "error": str(e)
                        }
                        yield json.dumps(error_response, ensure_ascii=False)
                        break

                    agent_task = asyncio.create_task(agent_iterator.__anext__())

            if progress_task is not None:
                progress_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await progress_task

            while not self.progress_queue.empty():
                try:
                    remaining = self.progress_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                yield json.dumps(remaining, ensure_ascii=False)

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            custom_logger.error(f"Error in process_query: {e}")
            custom_logger.error(error_trace)
            
            error_content = f"처리 중 오류가 발생했습니다. 다시 시도해주세요."
            error_metadata = {}
            
            # 에러 응답을 스트리밍으로 전송 (HTTPException 대신)
            error_response = {
                "step": "done",
                "message_id": str(uuid.uuid4()),
                "role": "assistant",
                "content": error_content,
                "metadata": error_metadata,
                "created_at": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            yield json.dumps(error_response, ensure_ascii=False)
        finally:
            if opik_tracer is not None:
                with contextlib.suppress(Exception):
                    opik_tracer.flush()

    @log_execution
    # 응답 metadata를 dict 형태로 안전하게 복사해 반환한다.
    def _handle_metadata(self, metadata) -> dict:
        custom_logger.info("========================================")
        custom_logger.info(metadata)
        result = {}
        if metadata:
            for k, v in metadata.items():
                result[k] = v
        return result
