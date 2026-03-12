from app.orchestration.streaming import (
    build_done_event,
    build_model_event,
    build_tools_event,
    serialize_event,
    serialize_sse_event,
)


def test_build_model_event():
    assert build_model_event(["Planning"]) == {
        "step": "model",
        "tool_calls": ["Planning"],
    }


def test_build_tools_event():
    assert build_tools_event("search_drug_info", {"count": 1}) == {
        "step": "tools",
        "name": "search_drug_info",
        "content": {"count": 1},
    }


def test_build_done_event():
    event = build_done_event(
        message_id="msg-1",
        content="완료",
        metadata={"tool_name": "search_drug_info"},
        created_at="2026-03-11T00:00:00",
        error="boom",
    )

    assert event == {
        "step": "done",
        "message_id": "msg-1",
        "role": "assistant",
        "content": "완료",
        "metadata": {"tool_name": "search_drug_info"},
        "created_at": "2026-03-11T00:00:00",
        "error": "boom",
    }


def test_serialize_sse_event():
    event = build_model_event(["Planning"])

    assert serialize_event(event) == '{"step": "model", "tool_calls": ["Planning"]}'
    assert (
        serialize_sse_event(event)
        == 'data: {"step": "model", "tool_calls": ["Planning"]}\n\n'
    )
