import os
import json

def read_json(file_path):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(f"{BASE_DIR}/data/{file_path}", 'r', encoding="utf-8") as file:
        data = json.load(file)
    return data

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
        