import asyncio
import contextlib
import uuid
from typing import Any

from app.core.config import settings
from app.orchestration.streaming import (
    build_done_event,
    build_model_event,
    build_tools_event,
)
from app.utils.logger import log_execution, custom_logger

from langchain_core.messages import HumanMessage


class AgentService:
    def __init__(self):
        self.agent = None

        self.progress_queue: asyncio.Queue = asyncio.Queue()

    def _create_agent(self, thread_id: uuid.UUID = None):
        """LangChain 에이전트 생성"""
        from app.agents.medical import create_medical_agent
        # 의료 agent 생성
        self.agent = create_medical_agent()

    def _get_or_create_agent(self, thread_id: uuid.UUID):
        if self.agent is None:
            self._create_agent(thread_id=thread_id)
        return self.agent

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

    def _build_error_event(self, content: str, error: Exception) -> dict[str, Any]:
        return build_done_event(
            message_id=str(uuid.uuid4()),
            content=content,
            metadata={},
            error=str(error),
        )

    def _extract_message_from_event(self, event: dict[str, Any]) -> Any | None:
        if not event:
            return None
        messages = event.get("messages", [])
        if not messages:
            return None
        return messages[0]

    def _build_final_response_event(self, tool_args: dict[str, Any]) -> dict[str, Any]:
        metadata = tool_args.get("metadata")
        custom_logger.info("========================================")
        custom_logger.info(tool_args)
        sanitized_content = self._sanitize_final_content(tool_args.get("content"))
        return build_done_event(
            message_id=tool_args.get("message_id"),
            content=sanitized_content,
            metadata=self._handle_metadata(metadata),
        )

    def _translate_model_step(self, message: Any) -> dict[str, Any] | None:
        tool_calls = message.tool_calls
        if not tool_calls:
            return None

        tool = tool_calls[0]
        if tool.get("name") in {"AgentResponse", "ChatResponse"}:
            return self._build_final_response_event(tool.get("args", {}))

        return build_model_event([tool["name"] for tool in tool_calls])

    def _translate_tools_step(self, message: Any) -> dict[str, Any]:
        return build_tools_event(message.name, message.content)

    def _translate_chunk_events(self, chunk: dict[str, Any]) -> list[dict[str, Any]]:
        translated_events: list[dict[str, Any]] = []

        for step, event in chunk.items():
            if not event or step not in ["model", "tools"]:
                continue

            message = self._extract_message_from_event(event)
            if message is None:
                continue

            if step == "model":
                translated = self._translate_model_step(message)
                if translated is not None:
                    translated_events.append(translated)

            if step == "tools":
                translated_events.append(self._translate_tools_step(message))

        return translated_events

    # 실제 대화 로직
    @log_execution
    async def process_query(self, user_messages: str, thread_id: uuid.UUID):
        """LangChain Messages 형식의 쿼리를 처리하고 AIMessage 형식으로 반환합니다."""
        try:
            agent = self._get_or_create_agent(thread_id=thread_id)

            custom_logger.info(f"사용자 메시지: {user_messages}")

            agent_stream = agent.astream(
                {"messages": [HumanMessage(content=user_messages)]},
                config={
                    "configurable": {"thread_id": str(thread_id)},
                    "recursion_limit": settings.DEEPAGENT_RECURSION_LIMIT,
                },
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
                        yield progress_event
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
                        yield self._build_error_event(
                            "처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                            e,
                        )
                        break

                    custom_logger.info(f"에이전트 청크: {chunk}")
                    try:
                        for translated_event in self._translate_chunk_events(chunk):
                            yield translated_event
                    except Exception as e:
                        # 청크 처리 중 예외 발생
                        custom_logger.error(f"Error processing chunk: {e}")
                        import traceback
                        custom_logger.error(traceback.format_exc())
                        yield self._build_error_event("데이터 처리 중 오류가 발생했습니다.", e)
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
                yield remaining

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            custom_logger.error(f"Error in process_query: {e}")
            custom_logger.error(error_trace)
            
            error_content = f"처리 중 오류가 발생했습니다. 다시 시도해주세요."
            error_metadata = {}
            
            # 에러 응답을 스트리밍으로 전송 (HTTPException 대신)
            yield self._build_error_event(error_content, e)

    @log_execution
    def _handle_metadata(self, metadata) -> dict:
        custom_logger.info("========================================")
        custom_logger.info(metadata)
        result = {}
        if metadata:
            for k, v in metadata.items():
                result[k] = v
        return result
