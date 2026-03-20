import os
import json

# app/data 아래 JSON 파일을 읽어 파이썬 객체로 반환한다.
def read_json(file_path):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(f"{BASE_DIR}/data/{file_path}", 'r', encoding="utf-8") as file:
        data = json.load(file)
    return data

# 메시지 목록 첫 항목에서 도구 호출명이 있는지 확인해 반환한다.
def check_tool_calls(json_data: dict):
    """
    주어진 JSON 데이터에서 도구 호출이 있는지 확인합니다.
    """
    
    messages = json_data.get("messages")
    if not isinstance(messages, list) or not messages:
        return None
    
    msg = messages[0]
    
    if hasattr(msg, "tool_calls"):
        if msg.tool_calls:
            tool_name = msg.tool_calls[0].get("name", "Unknown tool")
            return tool_name
        else:
            return None
    
    return None
        
