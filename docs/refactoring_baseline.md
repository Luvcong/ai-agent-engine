# Refactoring Baseline

이 문서는 safe incremental refactoring을 위한 현재 기준선입니다.
목표는 내부 구조를 개선하더라도 외부 동작은 유지하는 것입니다.

## 1. External behavior contracts

### `POST /api/v1/chat`

Current behavior:

- Response type: `text/event-stream`
- SSE payload format: each event is emitted as `data: <json>\n\n`
- Current event flow:
  1. Initial planning event from route layer
  2. Zero or more `model` events from `AgentService`
  3. Zero or more `tools` events from `AgentService`
  4. Final `done` event

Current event shapes:

- `model`
  - `{ "step": "model", "tool_calls": ["Planning"] }`
  - `{ "step": "model", "tool_calls": ["search_drug_info"] }`
- `tools`
  - `{ "step": "tools", "name": "<tool_name>", "content": <tool_result> }`
- `done`
  - `{ "step": "done", "message_id": "<uuid>", "role": "assistant", "content": "<text>", "metadata": <object>, "created_at": "<iso datetime>" }`
- error `done`
  - same shape as `done`, plus `error`

Compatibility rules:

- Keep the initial `Planning` event unless clients are migrated deliberately.
- Keep `step`, `tool_calls`, `name`, `content`, `message_id`, `role`, `metadata`, `created_at`, `error` field names stable.
- Keep `role="assistant"` for final events.

### `GET /api/v1/favorites/questions`

Current behavior:

- Returns JSON file contents directly
- Shape:
  - `{ "response": [ { "question_id", "title", "type", "created_at", "updated_at" } ] }`

### `GET /api/v1/threads`

Current behavior:

- Returns JSON file contents directly
- Shape:
  - `{ "response": [ { "thread_id", "title", "type", "created_at", "updated_at", "is_favorited" } ] }`

### `GET /api/v1/threads/{thread_id}`

Current behavior:

- Wraps a thread payload in `RootBaseModel[ThreadDataResponse]`
- Shape:
  - `{ "response": { "thread_id", "title", "messages": [...] } }`

## 2. Active runtime module map

Primary request flow:

- `app/main.py`
  - FastAPI app creation
  - lifespan for checkpointer
  - router registration
- `app/api/routes/chat.py`
  - `POST /api/v1/chat`
  - SSE response adapter
- `app/services/agent_service.py`
  - agent execution orchestration
  - LangChain stream to SSE-shaped JSON conversion
- `app/agents/medical.py`
  - `create_medical_agent()`
  - checkpointer lifecycle
- `app/prompt.py`
  - system prompt
- `app/tools/medical_tools.py`
  - LangChain tool layer
- `app/clients/public_data.py`
  - public API transport
  - response parsing
  - region/hospital query normalization
  - hospital result filtering

Thread/favorites read flow:

- `app/api/routes/threads.py`
- `app/services/threads_service.py`
- `app/utils/read_json.py`
- `app/models/threads.py`

Configuration and cross-cutting:

- `app/core/config.py`
- `app/utils/logger.py`
- `app/domain/hospital_mappings.py`

## 3. Legacy or non-primary modules

Historical legacy paths identified during refactoring:

- `app/services/conversation_service.py`
- `app/models/__init__.py`
- `langchain_test/`

These were not part of the main medical chat runtime path and have since been removed or isolated.

## 4. Current architectural risks to preserve during migration

- `app/services/agent_service.py` currently owns both orchestration and SSE JSON shaping.
- `app/clients/public_data.py` currently mixes infrastructure and domain logic.
- thread/favorites endpoints use file-backed JSON, while chat state uses LangGraph checkpointer storage.

These risks are known and intentionally unchanged in this baseline step.
