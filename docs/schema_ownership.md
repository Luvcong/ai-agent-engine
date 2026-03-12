# Schema Ownership

이 문서는 active runtime에서 사용하는 schema의 canonical ownership을 정리합니다.

## 1. Current canonical schemas for the active runtime

Active medical runtime 기준 canonical schema는 아래와 같습니다.

- chat request/response
  - `app/schemas/chat.py`
- thread read models
  - `app/schemas/threads.py`
- agent structured output
  - `app/schemas/agent_response.py`

현재 active runtime용 focused schema는 모두 `app/schemas/*`를 canonical implementation으로 사용합니다.

- `app/schemas/chat.py` is canonical
- `app/schemas/threads.py` is canonical
- `app/schemas/agent_response.py` is canonical

## 2. Why this step exists

초기에는 focused schema와 legacy model surface가 공존했지만, 현재는 active runtime 기준 canonical import entrypoint가 `app/schemas/*`로 정리되었습니다.

## 3. Rules for the next refactoring steps

- new code should prefer `app.schemas.*`
- no new code should reintroduce `app.models.*` imports
- legacy model package root has been removed

## 4. Planned migration sequence

1. introduce `app/schemas/*` as compatibility layer
2. migrate active runtime imports to `app.schemas.*`
3. move schema implementations module-by-module into `app/schemas/*`
4. keep tests green and external contracts unchanged
5. remove legacy model modules after confirming no remaining imports
