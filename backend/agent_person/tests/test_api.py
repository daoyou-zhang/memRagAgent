"""API 测试"""
import pytest
from fastapi.testclient import TestClient

from agent_person.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_root(client):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "agent_person"


def test_health(client):
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_chat_text(client):
    """测试文本聊天"""
    # TODO: 需要 mock daoyou_agent 服务
    pass


def test_voice_models(client):
    """测试语音模型列表"""
    response = client.get("/api/v1/digital-human/voices")
    assert response.status_code == 200
    assert "voices" in response.json()
