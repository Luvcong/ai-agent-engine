import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트 fixture"""
    return TestClient(app)


@pytest.fixture
def thread_id():
    """테스트용 thread_id 생성"""
    return str(uuid.uuid4())

