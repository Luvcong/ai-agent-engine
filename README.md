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

