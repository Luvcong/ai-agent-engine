import json
import uuid

from fastapi.testclient import TestClient

from app.services.agent_service import AgentService


def parse_sse_events(response_text: str) -> list[dict]:
    events = []
    for line in response_text.strip().splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_chat_sse_contract_baseline(client: TestClient, monkeypatch):
    async def fake_process_query(self, user_messages: str, thread_id: uuid.UUID):
        yield {"step": "model", "tool_calls": ["search_drug_info"]}
        yield {
            "step": "tools",
            "name": "search_drug_info",
            "content": {
                "query": {"item_name": "타이레놀"},
                "count": 1,
                "items": [{"item_name": "타이레놀정160mg"}],
            },
        }
        yield {
            "step": "done",
            "message_id": str(uuid.uuid4()),
            "role": "assistant",
            "content": "타이레놀 정보를 찾았습니다.",
            "metadata": {
                "tool_name": "search_drug_info",
                "query": {"item_name": "타이레놀"},
                "result": {"count": 1},
            },
            "created_at": "2026-03-11T00:00:00",
        }

    monkeypatch.setattr(AgentService, "process_query", fake_process_query)

    response = client.post(
        "/api/v1/chat",
        json={
            "thread_id": str(uuid.uuid4()),
            "message": "타이레놀이 어떤 약인지 알려줘",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    events = parse_sse_events(response.text)
    assert [event["step"] for event in events] == ["model", "model", "tools", "done"]

    assert events[0] == {"step": "model", "tool_calls": ["Planning"]}
    assert events[1] == {"step": "model", "tool_calls": ["search_drug_info"]}
    assert events[2]["name"] == "search_drug_info"
    assert events[2]["content"]["query"]["item_name"] == "타이레놀"

    done_event = events[3]
    assert done_event["step"] == "done"
    assert done_event["role"] == "assistant"
    assert done_event["content"] == "타이레놀 정보를 찾았습니다."
    assert done_event["metadata"]["tool_name"] == "search_drug_info"
    assert "message_id" in done_event
    assert "created_at" in done_event


def test_chat_sse_error_contract_baseline(client: TestClient, monkeypatch):
    async def fake_process_query(self, user_messages: str, thread_id: uuid.UUID):
        raise RuntimeError("boom")
        yield  # pragma: no cover

    monkeypatch.setattr(AgentService, "process_query", fake_process_query)

    response = client.post(
        "/api/v1/chat",
        json={
            "thread_id": str(uuid.uuid4()),
            "message": "에러 테스트",
        },
    )

    assert response.status_code == 200

    events = parse_sse_events(response.text)
    assert len(events) == 2
    assert events[0] == {"step": "model", "tool_calls": ["Planning"]}

    error_event = events[1]
    assert error_event["step"] == "done"
    assert error_event["role"] == "assistant"
    assert error_event["metadata"] == {}
    assert error_event["error"] == "boom"
    assert "message_id" in error_event
    assert "created_at" in error_event


def test_threads_list_contract_baseline(client: TestClient):
    response = client.get("/api/v1/threads")

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert isinstance(data["response"], list)
    assert data["response"]

    first = data["response"][0]
    assert {
        "thread_id",
        "title",
        "type",
        "created_at",
        "updated_at",
        "is_favorited",
    }.issubset(first.keys())


def test_favorite_questions_contract_baseline(client: TestClient):
    response = client.get("/api/v1/favorites/questions")

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert isinstance(data["response"], list)
    assert data["response"]

    first = data["response"][0]
    assert {
        "question_id",
        "title",
        "type",
        "created_at",
        "updated_at",
    }.issubset(first.keys())


def test_thread_detail_contract_baseline(client: TestClient):
    thread_id = "2f2a143c-04f4-4f52-9ca9-6b59da81bfc5"

    response = client.get(f"/api/v1/threads/{thread_id}")

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["response"]["thread_id"] == thread_id
    assert isinstance(data["response"]["messages"], list)
    assert data["response"]["messages"]

    first_message = data["response"]["messages"][0]
    assert {"message_id", "role", "content", "created_at"}.issubset(first_message.keys())
