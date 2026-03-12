# Medical Info Agent

공공데이터 API와 OpenAI LLM, LangChain Agent를 결합한 의료 정보 조회 서비스입니다.  
질병, 의약품, 병원, 지역 정보를 질문하면 Agent가 적절한 tool을 자동 선택해 공공데이터 기반 결과를 반환합니다.

## 개요

LangChain `create_agent()`를 사용하여 **의료 정보 조회 AI 에이전트**를 구현합니다.  
건강보험심사평가원 질병정보서비스, 식품의약품안전처 의약품개요정보(e약은요), 건강보험심사평가원 병원정보서비스를 활용해 질병 코드, 의약품 개요, 병원 기본정보를 종합적으로 제공합니다.

## 아키텍처

```text
사용자 질문
    ↓
LangChain Agent (OpenAI GPT-4.1)
    ↓ (LLM이 질문을 분석하여 필요한 도구를 자동 선택)
┌─────────────────────────────────────────────────────┐
│ Tool 1: search_disease_info       (HIRA 질병정보)   │
│ Tool 2: search_drug_info          (식약처 의약품)   │
│ Tool 3: resolve_region_information (지역명 판별)    │
│ Tool 4: search_hospital_info      (HIRA 병원정보)   │
└─────────────────────────────────────────────────────┘
    ↓
LLM 응답 (step:model -> step:tools -> step:done)
```

## 채팅으로 조회 가능한 기능

### Tool 1: `search_disease_info` - 질병명 / 질병코드 조회
- **API**: 건강보험심사평가원 질병정보서비스 `getDissNameCodeList1`
- **기능**: 질병명에 해당하는 질병코드와 명칭 조회
- **질문 예시**: `"결막염 질병코드 알려줘"`, `"감기 질병명 조회"`

### Tool 2: `search_drug_info` - 의약품 개요 조회
- **API**: 식품의약품안전처 의약품개요정보 `getDrbEasyDrugList`
- **기능**: 의약품명으로 효능, 사용법, 주의사항, 상호작용, 부작용, 보관법 조회
- **질문 예시**: `"타이레놀 정보 알려줘"`, `"후시딘 효능이 뭐야?"`

### Tool 3: `resolve_region_information` - 지역명 판별
- **기능**: 사용자가 입력한 지역명을 시도/시군구/읍면동 기준으로 해석
- **동작**: 공식 행정구역으로 판별되면 `resolved`, 아니면 `unresolved`
- **질문 예시**: `"서울 구로구 신도림동"`, `"신당동"`, `"잠실"`

### Tool 4: `search_hospital_info` - 병원 기본정보 조회
- **API**: 건강보험심사평가원 병원정보서비스 `getHospBasisList`
- **기능**: 병원명, 지역, 진료과, 종별, 좌표 반경 기반 병원 기본정보 조회
- **질문 예시**: `"서울아산병원 정보 알려줘"`, `"성동구 금호동 안과 찾아줘"`, `"구로구 정형외과 의원 알려줘"`

### 복합 질문
- `"금호동 안과 찾아줘"` -> 지역 판별 + 병원 검색
- `"타이레놀 정보 알려주고 부작용도 정리해줘"` -> 의약품 조회
- `"결막염 질병코드와 가까운 안과 알려줘"` -> 질병 조회 + 병원 검색

## 프로젝트 구조

```text
app/
├── agents/
│   ├── medical.py          # create_medical_agent(), checkpointer 초기화
│   └── prompts.py          # 의료 정보 조회 시스템 프롬프트
├── api/routes/
│   └── chat.py             # POST /api/v1/chat
├── clients/
│   └── public_data.py      # 공공데이터 API 비동기 client
├── core/
│   └── config.py           # OpenAI / 공공데이터 / 검색 limit 설정
├── domain/
│   └── hospital_mappings.py # 시도/시군구/병원종별/진료과 매핑
├── services/
│   └── agent_service.py    # Agent SSE 스트리밍 처리
└── tools/
    └── medical_tools.py    # LangChain tool 정의
```

## 외부 API 및 환경 변수

### 사용 API
- 건강보험심사평가원 질병정보서비스
- 식품의약품안전처 의약품개요정보(e약은요)
- 건강보험심사평가원 병원정보서비스

### API 키 설정

```env
API_V1_PREFIX=/api/v1
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1
PUBLIC_DATA_API_KEY=...
PUBLIC_DATA_TIMEOUT=20
SQLITE_CHECKPOINTER_PATH=app/data/checkpoints.db
```

## 핵심 구현 포인트

### 1. LangChain `create_agent()`
- `langchain.agents.create_agent(model, tools, system_prompt)` 사용
- Agent가 질문 맥락에 따라 tool을 선택
- `astream(stream_mode="updates")`로 SSE 스트리밍 응답 생성

### 2. 지역명 판별과 병원 검색 분리
- `resolve_region_information`으로 지역을 먼저 해석할 수 있음
- `서울`, `경기`, `구로구` 같은 지역명은 내부 시도/시군구 코드로 매핑
- `신당동`, `서초동`처럼 `동/읍/면/리`로 끝나는 지역명은 자동으로 추출하여 `emdong_name` 검색 파라미터로 사용
- 공식 행정구역으로 판별되지 않는 생활권/별칭 표현은 자동 추정하지 않고 재질문 유도

### 3. 병원 검색 파라미터 확장
- 이름/지역
  - `hospital_name`
  - `region_keyword`
  - `sido_code`
  - `sggu_code`
  - `emdong_name`
- 병원 속성
  - `hospital_type_name`
  - `hospital_type_code`
  - `department_name`
  - `department_code`
- 위치 기반
  - `x_pos`
  - `y_pos`
  - `radius`

### 4. 넓은 병원 검색 보정
- 병원명 없이 시도/시군구/읍면동, 종별, 진료과 조건이 있는 검색은
  API 요청 건수를 최대 30건까지 자동으로 늘려 후보를 더 확보
- 진료과명이 병원명에 직접 포함된 결과가 있으면 해당 결과를 우선 사용

### 5. 체크포인터
- 대화 문맥은 `thread_id` 기준으로 SQLite checkpointer에 저장
- FastAPI lifespan에서 checkpointer를 열고 닫음
- 저장 파일은 RAM이 아니라 디스크에 유지되므로 서버 재시작 후에도 멀티턴 상태 유지 가능

## SSE 스트리밍 프로토콜

```text
step: "model" -> 에이전트가 도구 호출을 결정 (tool_calls 배열)
step: "tools" -> 도구 실행 결과 반환
step: "done"  -> 최종 답변 (message_id, content, metadata)
```

## 실행 방법

```bash
cp env.sample .env
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

문서: `http://localhost:8000/docs`

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
    "message": "성동구 금호동 안과 있어?"
  }'
```

## 테스트

```bash
uv run pytest
```

<br>
<br>
<br>

---

<details> <summary><b>README_ver1</b></summary> <br>

# Agent Education Template

FastAPI 기반의 LangChain v1.0 에이전트 교육용 템플릿입니다.

## 기술 스택

- FastAPI
- LangChain v1.0
- OpenAI (GPT-4)
- uv (패키지 관리)

## 환경 준비 및 설치 가이드 (교육생용)

본 에이전트 프로젝트는 파이썬 패키지 매니저로 **`uv`**를 사용합니다. 아래 절차에 따라 실습 환경을 구성해 주세요.

### 1. 사전 요구사항
* Python 3.11 이상 3.13 이하 버전을 권장합니다.
* `uv` 패키지 매니저 설치:
  ```bash
  # macOS / Linux / Windows (WSL)
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### 2. 프로젝트 의존성 설치
프로젝트 폴더(`agent`)로 이동한 뒤, 아래 명령어를 실행하여 가상환경 세팅 및 관련 패키지 설치를 진행합니다.

```bash
# 파이썬 의존성 동기화 및 가상환경(.venv) 자동 생성
uv sync
```
* 명령어가 정상적으로 완료되면 프로젝트 디렉토리 내에 `.venv` 폴더가 생성됩니다.

### 3. 환경 변수 설정
에이전트 구동을 위해 필요한 API 키 등을 설정해야 합니다.

1. 프로젝트 루트 경로의 `env.sample` 파일을 복사하여 `.env` 파일을 생성합니다.
   ```bash
   cp env.sample .env
   ```
2. 생성된 `.env` 파일을 열고, 아래와 같이 본인의 **OpenAI API Key**를 입력합니다.
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o  # 또는 gpt-4
   ```

### 4. 개발 서버 실행

환경변수 세팅까지 끝났다면 가상 환경 내에서 서버를 구동합니다.

```bash
# uvicorn 서버 실행
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
서버가 성공적으로 구동되면 브라우저에서 `http://localhost:8000/docs` 로 접속하여 API 문서를 확인할 수 있습니다.

## 프로젝트 구조

```
agent/
├── app/
│   ├── api/              # API 엔드포인트
│   │   └── routes/       # 라우트 정의
│   ├── core/             # 설정 및 초기화
│   │   └── config.py     # 설정 관리
│   ├── models/           # 데이터 모델
│   ├── services/         # 비즈니스 로직
│   │   └── agent_service.py  # 에이전트 서비스
│   ├── utils/            # 유틸리티 함수
│   └── main.py           # FastAPI 앱 진입점
├── tests/                # 테스트 코드
├── pyproject.toml        # 프로젝트 설정 및 의존성
└── README.md
```

## API 엔드포인트

- `GET /`: API 정보
- `GET /health`: 헬스 체크
- `POST /api/query/`: 자연어 쿼리 처리

</details>
