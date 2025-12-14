"""pytest 公共配置

提供测试所需的 fixtures 和配置
"""
import os
import pytest
import httpx
from typing import Generator

# 服务地址配置
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://127.0.0.1:5000")
KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://127.0.0.1:5001")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8000")


@pytest.fixture(scope="session")
def memory_client() -> Generator[httpx.Client, None, None]:
    """Memory 服务 HTTP 客户端"""
    with httpx.Client(base_url=MEMORY_SERVICE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def knowledge_client() -> Generator[httpx.Client, None, None]:
    """Knowledge 服务 HTTP 客户端"""
    with httpx.Client(base_url=KNOWLEDGE_SERVICE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def agent_client() -> Generator[httpx.Client, None, None]:
    """Agent 服务 HTTP 客户端"""
    with httpx.Client(base_url=AGENT_SERVICE_URL, timeout=60.0) as client:
        yield client


@pytest.fixture
def test_user_id() -> str:
    """测试用户 ID"""
    return "test_user_001"


@pytest.fixture
def test_project_id() -> str:
    """测试项目 ID"""
    return "test_project_001"


@pytest.fixture
def test_session_id() -> str:
    """测试会话 ID"""
    return "test_session_001"
