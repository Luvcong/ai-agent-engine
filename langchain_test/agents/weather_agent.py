from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from prompts.weather_prompt import SYSTEM_PROMPT
from tools.weather_tools import get_weather_for_location, get_user_location
from schemas.response_format import ResponseFormat
from langgraph.checkpoint.memory import InMemorySaver

# Agent State를 RAM에 저장
checkpointer = InMemorySaver()

def create_weather_agent():
    agent = create_agent(
        model="gpt-4o",
        tools=[
            get_weather_for_location,
            get_user_location
        ],
        system_prompt=SYSTEM_PROMPT,
        response_format=ToolStrategy(ResponseFormat),
        checkpointer=checkpointer
    )
    return agent