# Medical Info Agent API Spec

## Base

- Base URL: `http://localhost:8000`
- Prefix: `/api/v1`

## POST `/api/v1/chat`

사용자 질문을 받아 LangChain Agent가 적절한 공공데이터 tool을 선택하고 SSE로 응답합니다.

### Request

```json
{
  "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "타이레놀이 어떤 약인지 알려줘"
}
```

### SSE Response Example

```json
{"step":"model","tool_calls":["Planning"]}
{"step":"model","tool_calls":["search_drug_info"]}
{"step":"tools","name":"search_drug_info","content":{"query":{"item_name":"타이레놀"},"count":1,"items":[{"item_name":"타이레놀정160mg"}]}}
{"step":"done","message_id":"...","role":"assistant","content":"타이레놀 정보를 찾았습니다.","metadata":{"tool_name":"search_drug_info","query":{"item_name":"타이레놀"},"result":{"count":1}},"created_at":"2026-03-11T00:00:00"}
```

## Tool Mapping

- 질병 질문 -> `search_disease_info`
- 의약품 질문 -> `search_drug_info`
- 병원 질문 -> `search_hospital_info`
- 약국 질문 -> `search_pharmacy_info`
- 지역 해석 질문 -> `resolve_region_information`

## Internal flow

현재 내부 처리 흐름은 다음과 같습니다.

```text
chat route
-> AgentService
-> LangChain agent
-> medical tools
-> MedicalSearchService
-> PublicMedicalDataClient
-> domain/infrastructure helpers
```

SSE event 생성과 serialization은 `app/orchestration/streaming.py`에서 담당합니다.
