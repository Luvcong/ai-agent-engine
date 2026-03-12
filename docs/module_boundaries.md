# Module Boundaries

이 문서는 현재 저장소의 module category를 명시적으로 나누고, safe refactoring 동안 지켜야 할 dependency direction을 고정합니다.

## 1. Module categories

### Active runtime modules

These modules are part of the current medical agent runtime path.

- `app/main.py`
- `app/api/routes/chat.py`
- `app/api/routes/threads.py`
- `app/services/agent_service.py`
- `app/services/threads_service.py`
- `app/agents/medical.py`
- `app/prompt.py`
- `app/tools/medical_tools.py`
- `app/clients/public_data.py`
- `app/core/config.py`
- `app/domain/hospital_mappings.py`
- `app/models/chat.py`
- `app/models/threads.py`
- `app/models/agent_response.py`
- `app/utils/logger.py`
- `app/utils/read_json.py`

### Legacy or non-primary modules

These modules are present in the repository but are not part of the primary medical chat runtime.

- `langchain_test/`
`langchain_test/` has already been removed as cleanup. Historical mentions remain only for migration context.

## 2. Current allowed dependency direction

Current target direction:

- `api -> services | schemas`
- `services -> agents | schemas | utils`
- `agents -> tools | prompts | schemas | core`
- `tools -> clients | core`
- `clients -> domain | core`
- `threads route/service -> thread schemas | json utils`

Current anti-goals:

- active runtime modules reintroducing a legacy `app.models` package root
- active runtime modules importing anything under `langchain_test`

## 3. Boundary notes

### Legacy cleanup status

The old `app.models` package root and `conversation_service` path were removed after confirming they were not used by the active runtime.
The canonical schema entrypoint is now `app.schemas.*`.

## 4. Migration rule for the next steps

Before moving files or deleting code:

1. preserve current external API contracts
2. move imports away from legacy modules
3. add adapters or re-exports if needed
4. delete legacy code only after active runtime no longer depends on it
