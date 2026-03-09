import pytest
import json
import uuid
from fastapi.testclient import TestClient
from typing import List, Dict, Any


def parse_sse_response(response_text: str) -> List[Dict[str, Any]]:
    """SSE 응답을 파싱하는 헬퍼 함수"""
    events = []
    for line in response_text.strip().split('\n'):
        if line.startswith('data: '):
            data_str = line[6:]  # 'data: ' 제거
            if data_str == '[DONE]':
                break
            try:
                events.append(json.loads(data_str))
            except json.JSONDecodeError:
                pass
    return events


@pytest.mark.order(3)
def test_case1_simple_sql_generation(client: TestClient, thread_id: str):
    """
    Case 1: 단순 SQL 생성
    사용자 질문: "2008년 12월 조직별 유동자산 금액을 조회해줘"
    """
    response = client.post(
        "/api/v1/chat",
        json={
            "thread_id": thread_id,
            "message": "2008년 12월 조직별 유동자산 금액을 조회해줘"
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # SSE 응답 파싱
    events = parse_sse_response(response.text)
    
    # 최종 응답 확인
    final_events = [e for e in events if e.get("type") == "final_response"]
    assert len(final_events) > 0
    
    final_message = json.loads(final_events[0]["message"])
    assert "metadata" in final_message
    assert final_message["metadata"]["sql"] is not None
    assert "유동자산" in final_message["metadata"]["sql"]
    assert "200812" in final_message["metadata"]["sql"]


@pytest.mark.order(4)
def test_case2_grid_generation(client: TestClient, thread_id: str):
    """
    Case 2: Grid까지 생성
    사용자 질문: "2009년 1월 조직별 제조원가 금액 상위 5개를 보여줘"
    """
    response = client.post(
        "/api/v1/chat",
        json={
            "thread_id": thread_id,
            "message": "2009년 1월 조직별 제조원가 금액 상위 5개를 보여줘"
        }
    )
    
    assert response.status_code == 200
    
    events = parse_sse_response(response.text)
    final_events = [e for e in events if e.get("type") == "final_response"]
    assert len(final_events) > 0
    
    final_message = json.loads(final_events[0]["message"])
    assert final_message["metadata"]["sql"] is not None
    assert final_message["metadata"]["data"] is not None
    assert "columns" in final_message["metadata"]["data"]
    assert "rows" in final_message["metadata"]["data"]
    assert "제조원가" in final_message["metadata"]["sql"]
    assert "200901" in final_message["metadata"]["sql"]
    assert "LIMIT 5" in final_message["metadata"]["sql"]


@pytest.mark.order(5)
def test_case3_chart_generation_multiturn(client: TestClient):
    """
    Case 3: Chart까지 생성 (멀티턴)
    1차: "2009년 12월 본부별 총 인건비 보여줘"
    2차: "부서별로 상세하게 바꿔줘"
    3차: "인당 평균 인건비도 같이 보여줘"
    """
    thread_id = str(uuid.uuid4())
    
    # 1차 요청
    response1 = client.post(
        "/api/v1/chat",
        json={
            "thread_id": thread_id,
            "message": "2009년 12월 본부별 총 인건비 보여줘"
        }
    )
    
    assert response1.status_code == 200
    events1 = parse_sse_response(response1.text)
    final1 = [e for e in events1 if e.get("type") == "final_response"]
    assert len(final1) > 0
    
    msg1 = json.loads(final1[0]["message"])
    assert "본부" in msg1["metadata"]["sql"] or "head_nm" in msg1["metadata"]["sql"]
    assert msg1["metadata"]["chart"] is not None
    
    # 2차 요청
    response2 = client.post(
        "/api/v1/chat",
        json={
            "thread_id": thread_id,
            "message": "부서별로 상세하게 바꿔줘"
        }
    )
    
    assert response2.status_code == 200
    events2 = parse_sse_response(response2.text)
    final2 = [e for e in events2 if e.get("type") == "final_response"]
    assert len(final2) > 0
    
    msg2 = json.loads(final2[0]["message"])
    assert "dept_nm" in msg2["metadata"]["sql"] or "부서" in msg2["metadata"]["sql"]
    
    # 3차 요청
    response3 = client.post(
        "/api/v1/chat",
        json={
            "thread_id": thread_id,
            "message": "인당 평균 인건비도 같이 보여줘"
        }
    )
    
    assert response3.status_code == 200
    events3 = parse_sse_response(response3.text)
    final3 = [e for e in events3 if e.get("type") == "final_response"]
    assert len(final3) > 0
    
    msg3 = json.loads(final3[0]["message"])
    assert "avg_pay_per_person" in msg3["metadata"]["sql"] or "평균" in msg3["metadata"]["sql"]
    assert len(msg3["metadata"]["data"]["columns"]) == 3  # dept_nm, total_pay, avg_pay_per_person


@pytest.mark.order(6)
def test_case4_item_inquiry_multiturn(client: TestClient):
    """
    Case 4: 항목 조회 요청 (멀티턴)
    1차: "우리 DB에서 제조원가는 어디서 확인할 수 있어?"
    2차: "유동자산이랑 비유동자산 차이가 뭐야?"
    """
    thread_id = str(uuid.uuid4())
    
    # 1차 요청
    response1 = client.post(
        "/api/v1/chat",
        json={
            "thread_id": thread_id,
            "message": "우리 DB에서 제조원가는 어디서 확인할 수 있어?"
        }
    )
    
    assert response1.status_code == 200
    events1 = parse_sse_response(response1.text)
    final1 = [e for e in events1 if e.get("type") == "final_response"]
    assert len(final1) > 0
    
    msg1 = json.loads(final1[0]["message"])
    assert "제조원가" in msg1["content"]
    assert "f_pl" in msg1["content"]
    assert msg1["metadata"]["sql"] is None  # SQL 생성 없음
    
    # 2차 요청
    response2 = client.post(
        "/api/v1/chat",
        json={
            "thread_id": thread_id,
            "message": "유동자산이랑 비유동자산 차이가 뭐야?"
        }
    )
    
    assert response2.status_code == 200
    events2 = parse_sse_response(response2.text)
    final2 = [e for e in events2 if e.get("type") == "final_response"]
    assert len(final2) > 0
    
    msg2 = json.loads(final2[0]["message"])
    assert "유동자산" in msg2["content"]
    assert "비유동자산" in msg2["content"]
    assert "f_bs" in msg2["content"]
    assert msg2["metadata"]["sql"] is None  # SQL 생성 없음
