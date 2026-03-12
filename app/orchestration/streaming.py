from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any


def build_model_event(tool_calls: list[str]) -> dict[str, Any]:
    return {"step": "model", "tool_calls": tool_calls}


def build_tools_event(name: str | None, content: Any) -> dict[str, Any]:
    return {"step": "tools", "name": name, "content": content}


def build_done_event(
    *,
    message_id: str,
    content: str,
    metadata: dict[str, Any],
    created_at: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    event = {
        "step": "done",
        "message_id": message_id,
        "role": "assistant",
        "content": content,
        "metadata": metadata,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }
    if error is not None:
        event["error"] = error
    return event


def serialize_event(event: dict[str, Any]) -> str:
    return json.dumps(event, ensure_ascii=False)


def serialize_sse_event(event: dict[str, Any]) -> str:
    return f"data: {serialize_event(event)}\n\n"
