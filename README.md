# Medical Info Agent

공공데이터 API와 OpenAI LLM, LangChain Agent를 결합한 의료 정보 조회 서비스입니다.  
질병, 의약품, 병원, 약국, 지역 정보를 질문하면 agent가 적절한 tool을 선택해 공공데이터 기반 결과를 반환합니다.

## 개요

이 프로젝트는 FastAPI 서버 위에서 LangChain `create_agent()` 기반 의료 정보 agent를 제공합니다.

사용하는 공공데이터 API:

- 건강보험심사평가원 질병정보서비스
- 식품의약품안전처 의약품개요정보(e약은요)
- 건강보험심사평가원 병원정보서비스
- 건강보험심사평가원 약국정보서비스
- Elasticsearch 질병 문서 인덱스 (`edu-collection`)

핵심 목표:

- 의료 정보 질의에 맞는 tool 자동 선택
- 공공데이터 기반 결과만 반환
- SSE 스트리밍으로 단계별 응답 제공
- `thread_id` 기반 멀티턴 문맥 유지

## 제공 기능

### 1. `search_disease_info`

- 용도: 질병명으로 질병코드와 명칭 조회
- API: `getDissNameCodeList1`
- 예시 질문:
  - `결막염 질병코드 알려줘`
  - `감기 질병명 조회`

### 2. `search_drug_info`

- 용도: 의약품명으로 효능, 복용법, 주의사항, 상호작용, 부작용, 보관법 조회
- API: `getDrbEasyDrugList`
- 예시 질문:
  - `타이레놀 정보 알려줘`
  - `후시딘 효능이 뭐야?`

### 3. `resolve_region_information`

- 용도: 입력한 지역 표현을 시/도, 시/군/구, 동/읍/면 기준으로 해석
- 결과:
  - 공식 행정구역 해석 가능 시 `resolved`
  - 해석이 불충분하면 `unresolved`
- 예시 질문:
  - `서울 구로구 신도림동`
  - `신당동`
  - `잠실`

### 4. `search_hospital_info`

- 용도: 병원명, 지역, 진료과, 종별, 좌표 반경 기반 병원 조회
- API: `getHospBasisList`
- 예시 질문:
  - `서울아산병원 정보 알려줘`
  - `성동구 금호동 안과 찾아줘`
  - `구로구 정형외과 의원 알려줘`

### 5. `search_pharmacy_info`

- 용도: 약국명, 지역, 좌표 반경 기반 약국 조회
- API: `getParmacyBasisList`
- 예시 질문:
  - `신도림동 약국 찾아줘`
  - `서울 구로구 온누리약국 알려줘`
  - `근처 약국 찾아줘`

### 복합 질문 예시

- `금호동 안과 찾아줘` -> 지역 판별 + 병원 검색
- `결막염 질병코드와 가까운 안과 알려줘` -> 질병 조회 + 병원 검색
- `신도림동 약국 찾아줘` -> 지역 판별 + 약국 검색

## 현재 아키텍처

```text
사용자 질문
    ↓
FastAPI Route
    ↓
AgentService
    ↓
LangChain Agent (OpenAI)
    ↓
LangChain Tools
    ↓
MedicalSearchService
    ↓
PublicMedicalDataClient
    ├─ domain helpers
    │  ├─ region_resolution
    │  └─ hospital_search
    └─ infrastructure helpers
       ├─ public_data transport
       └─ public_data parsers
    ↓
SSE 응답 (step:model -> step:tools -> step:done)
```

의존 방향:

```text
api -> orchestration/services -> domain -> infrastructure
api -> schemas
tools -> services
services -> clients
clients -> domain/infrastructure
```

## 프로젝트 구조

```text
app/
├── agents/
│   └── medical.py
├── api/routes/
│   ├── chat.py
│   └── threads.py
├── clients/
│   └── public_data.py
├── core/
│   └── config.py
├── data/
│   ├── checkpoints.db
│   ├── favorite_questions.json
│   ├── threads.json
│   └── threads/
├── domain/
│   ├── hospital_mappings.py
│   ├── hospital_search.py
│   └── region_resolution.py
├── infrastructure/public_data/
│   ├── parsers.py
│   └── transport.py
├── orchestration/
│   └── streaming.py
├── schemas/
│   ├── agent_response.py
│   ├── chat.py
│   └── threads.py
├── services/
│   ├── agent_service.py
│   ├── medical_search_service.py
│   └── threads_service.py
├── tools/
│   └── medical_tools.py
└── main.py
```

## 핵심 설계 포인트

### Tool -> Service -> Client 분리

- `medical_tools.py`는 LangChain tool adapter 역할만 담당
- `MedicalSearchService`는 기본 `limit` 정책과 결과 truncation 등 use-case 책임 담당
- `PublicMedicalDataClient`는 조회용 facade 역할 담당

### Domain / Infrastructure 분리

- 지역 해석, 병원 검색 정규화/필터링은 `app/domain`
- HTTP 요청, XML/JSON parsing은 `app/infrastructure/public_data`

### Shared HTTP Client

- 공공데이터 API 호출용 `httpx.AsyncClient`는 앱 lifespan 동안 재사용
- 요청마다 새 connection pool을 만들지 않고 shared client를 사용
- Elasticsearch 조회용 `httpx.AsyncClient`도 앱 lifespan 동안 재사용

### Checkpointer

- 대화 문맥은 `thread_id` 기준으로 SQLite checkpointer에 저장
- 서버 재시작 후에도 멀티턴 상태 유지 가능

### SSE Streaming

- `step: "model"`: agent가 tool 호출을 결정
- `step: "tools"`: tool 실행 결과 반환
- `step: "done"`: 최종 응답 반환

## 지역 해석 정책

현재 지역 해석은 공식 행정구역 기준으로 동작합니다.

- `SIDO_CODE_MAP` 기반 시/도 탐색
- `SGGU_CODE_MAP` 기반 시/군/구 탐색
- `동/읍/면/리` 토큰 탐색

정책상:

- 공식 행정구역은 가능한 범위에서 구조화
- 역명, 생활권, 지역 별칭은 무리하게 확정하지 않음
- 해석이 불충분하면 `unresolved`로 처리하고 사용자에게 상세 주소를 다시 요청

## 병원/약국 검색 정책

병원과 약국 검색은 공통적으로 지역 해석 helper를 재사용합니다.

지원 파라미터 예시:

- 이름: `hospital_name`, `pharmacy_name`
- 지역: `region_keyword`, `sido_code`, `sggu_code`, `emdong_name`
- 속성: `hospital_type_name`, `hospital_type_code`, `department_name`, `department_code`
- 위치: `x_pos`, `y_pos`, `radius`

넓은 지역 검색 보정:

- 병원명/약국명 없이 지역 조건만 있는 검색은 API 요청 건수를 최대 30건까지 자동 확대

## API

### Base

- Base URL: `http://localhost:8000`
- Prefix: `/api/v1`

### `POST /api/v1/chat`

Request:

```json
{
  "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "서울아산병원 정보 알려줘"
}
```

SSE Response Example:

```json
{"step":"model","tool_calls":["Planning"]}
{"step":"model","tool_calls":["search_hospital_info"]}
{"step":"tools","name":"search_hospital_info","content":{"query":{"hospital_name":"서울아산병원"},"count":1,"items":[{"hospital_name":"서울아산병원"}]}}
{"step":"done","message_id":"...","role":"assistant","content":"서울아산병원 정보를 찾았습니다.","metadata":{"tool_name":"search_hospital_info","result":{"count":1}},"created_at":"2026-03-11T00:00:00+00:00"}
```

### `GET /api/v1/threads`

- 최근 대화 목록 조회

### `GET /api/v1/threads/{thread_id}`

- 특정 대화 세션 조회

### `GET /api/v1/favorites/questions`

- 즐겨찾기 질문 목록 조회

자세한 스펙은 [docs/spec.md](/Users/jinheekim/didim/project/ai_agent/agent/docs/spec.md)를 참고하세요.

## 환경 변수

```env
API_V1_PREFIX=/api/v1
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1
PUBLIC_DATA_API_KEY=...
PUBLIC_DATA_TIMEOUT=20
SQLITE_CHECKPOINTER_PATH=app/data/checkpoints.db
```

## 실행 방법

```bash
cp env.sample .env
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

문서:

- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## 예시 요청

```bash
curl -N -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "message": "서울아산병원 정보 알려줘"
  }'
```

```bash
curl -N -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "message": "서울 구로구 신도림동 약국 찾아줘"
  }'
```

## 테스트

```bash
uv run pytest
```

현재 테스트는 다음 범위를 다룹니다.

- API contract baseline
- SSE event serialization
- tool behavior
- `MedicalSearchService` 정책
- module boundary
- shared public-data transport 재사용

## 참고 문서

- [docs/spec.md](/Users/jinheekim/didim/project/ai_agent/agent/docs/spec.md)
- [docs/refactoring_baseline.md](/Users/jinheekim/didim/project/ai_agent/agent/docs/refactoring_baseline.md)
- [docs/module_boundaries.md](/Users/jinheekim/didim/project/ai_agent/agent/docs/module_boundaries.md)
- [docs/schema_ownership.md](/Users/jinheekim/didim/project/ai_agent/agent/docs/schema_ownership.md)
