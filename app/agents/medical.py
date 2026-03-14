from __future__ import annotations

from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.prompts import SYSTEM_PROMPT
from app.core.config import settings
from app.models.agent_response import AgentResponse
from app.tools.medical_tools import (
    resolve_region_information,
    search_disease_knowledge,
    search_disease_info,
    search_drug_info,
    search_hospital_info,
    search_pharmacy_info,
)

try:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
except ModuleNotFoundError:  # pragma: no cover - package installed after uv sync
    AsyncSqliteSaver = None


# FastAPI lifespan 동안 하나의 checkpointer 인스턴스를 재사용
_checkpointer = None
_checkpointer_context = None


async def init_checkpointer():
    global _checkpointer, _checkpointer_context
    if _checkpointer is not None:
        return _checkpointer

    # SQLite saver 패키지가 아직 없으면 MemorySaver 사용
    if AsyncSqliteSaver is None:
        _checkpointer = InMemorySaver()
        return _checkpointer

    db_path = Path(settings.SQLITE_CHECKPOINTER_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    _checkpointer_context = AsyncSqliteSaver.from_conn_string(str(db_path))
    _checkpointer = await _checkpointer_context.__aenter__()
    return _checkpointer


async def close_checkpointer():
    global _checkpointer, _checkpointer_context
    if _checkpointer_context is not None:
        await _checkpointer_context.__aexit__(None, None, None)
    _checkpointer = None
    _checkpointer_context = None


def get_checkpointer():
    # lifespan이 없는 상황에서는 메모리 saver 사용
    if _checkpointer is None:
        return InMemorySaver()
    return _checkpointer


def create_medical_agent():
    model = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    return create_agent(
        model=model,
        tools=[
            resolve_region_information,  # 지역명 정규화
            search_disease_knowledge, # 질병설명/가이드라인조회
            search_disease_info,     # 질병정보조회
            search_drug_info,        # 의약품정보조회
            search_hospital_info,    # 병원정보조회
            search_pharmacy_info,    # 약국정보조회
        ],
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(AgentResponse),
        checkpointer=get_checkpointer(),
    )
