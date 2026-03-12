# 설명
LangChain Docs의 Quickstart 예제를 기반으로 작성한 Agent + Tool 호출 테스트 코드입니다.
사용자의 질문을 Agent가 분석하고, 필요한 경우 Tool을 호출하여 최종 응답을 생성하는 흐름을 확인하기 위한 목적입니다.

## 확인 가능한 기능
- LangChain Agent 생성
- Tool 등록 및 호출
- Agent의 reasoning 과정
- ToolRuntime을 통한 runtime context 전달
- Agent 실행 결과 구조 확인

## 테스트 프로젝트 구조
langchain_test
│
├ main.py                 # Agent 실행 테스트 코드
│
├ agent                   # LangChain Agent 생성 로직
│  └ weather_agent.py
│
├ prompts                 # System Prompt 정의
│  └ weather_prompt.py
│
├ tools                   # Agent가 사용할 Tool 정의
│  └ weather_tools.py
│
└ schemas                 # 응답형식 스키마 정의
   └ response_format.py