import pytest
from fastapi.testclient import TestClient

@pytest.mark.order(1)
def test_root_endpoint(client: TestClient):
    """루트 엔드포인트 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["message"] == "Edu Agent API"
    assert data["version"] == "0.1.0"

@pytest.mark.order(2)
def test_health_endpoint(client: TestClient):
    """헬스 체크 엔드포인트 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"

