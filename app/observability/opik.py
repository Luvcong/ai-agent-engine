from __future__ import annotations

import os
from functools import lru_cache

import opik
from opik.integrations.langchain import OpikTracer

from app.core.config import settings
from app.utils.logger import custom_logger


# 환경 변수와 설정 객체를 순서대로 확인해 Opik 설정값을 읽어온다.
def _read_opik_value(env_name: str, settings_attr: str) -> str | None:
    value = os.getenv(env_name)
    if value:
        return value

    opik_settings = settings.OPIK
    if opik_settings is None:
        return None

    nested_value = getattr(opik_settings, settings_attr, None)
    return nested_value or None


@lru_cache(maxsize=1)
# Opik 추적 설정을 한 번만 초기화하고 활성화 여부를 반환한다.
def configure_opik() -> bool:
    opik_settings = settings.OPIK
    if opik_settings is not None and not opik_settings.ENABLED:
        custom_logger.info("Opik is disabled because OPIK__ENABLED is set to false.")
        return False

    api_key = _read_opik_value("OPIK_API_KEY", "API_KEY")
    workspace = _read_opik_value("OPIK_WORKSPACE", "WORKSPACE")
    url_override = _read_opik_value("OPIK_URL_OVERRIDE", "URL_OVERRIDE")

    if not any([api_key, workspace, url_override]):
        custom_logger.info("Opik is disabled because no configuration was provided.")
        return False

    try:
        opik.configure(
            api_key=api_key,
            workspace=workspace,
            url=url_override,
            use_local=not bool(api_key),
        )
    except Exception as exc:  # pragma: no cover - network/config issue
        custom_logger.exception("Failed to configure Opik: %s", exc)
        return False

    custom_logger.info("Opik tracing is enabled.")
    return True


# 주어진 thread_id에 연결된 LangChain용 Opik tracer를 생성한다.
def create_opik_tracer(thread_id: str) -> OpikTracer | None:
    if not configure_opik():
        return None

    project_name = _read_opik_value("OPIK_PROJECT_NAME", "PROJECT")

    return OpikTracer(
        project_name=project_name,
        thread_id=thread_id,
        tags=["medical-agent"],
        metadata={
            "service": "medical-info-agent",
            "model": settings.OPENAI_MODEL,
        },
    )
