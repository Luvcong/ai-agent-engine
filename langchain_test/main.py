from dotenv import load_dotenv
from agents.weather_agent import create_weather_agent
from tools.weather_tools import Context

load_dotenv()

# agent 생성
agent = create_weather_agent()

# thread_id 설정
config = {"configurable": {"thread_id": "1"}}

# 첫번째 질문
result = agent.invoke(
    {
        "messages": [{
            "role": "user",
            "content": "what's the weather where I am?"     # 사용자 메시지
        }]
    },
    context = Context(user_id = "1"),    # tool이 사용할 runtime 데이터
    config = config
)

print('>>> MESSAGES (1) : ', result["structured_response"])

# 두번째 질문
result = agent.invoke(
    {
        "messages" : [{
            "role" : "user",
            "content" : "한국어로 대답해줘"
        }]
    },
    context = Context(user_id = "1"),
    config = config
)

print('>>> MESSAGES (2) : ', result["structured_response"])