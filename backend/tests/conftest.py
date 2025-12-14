"""pytest 公共配置

提供测试所需的 fixtures 和配置
支持两种测试模式：
1. 管理员模式 - 使用 ADMIN_API_KEY，可访问所有数据
2. 工程模式 - 使用 project_id，只能访问该工程的数据

配置来源：test_config.py（集中管理测试用户和 API Key）
"""
import pytest
import httpx
from typing import Generator

# 从 test_config 导入所有配置
from test_config import (
    MEMORY_SERVICE_URL,
    KNOWLEDGE_SERVICE_URL,
    AGENT_SERVICE_URL,
    ADMIN,
    TENANT_A,
    TENANT_B,
    TEST_USER_1,
    TEST_USER_2,
    TEST_USER_3,
    TEST_SESSIONS,
    get_admin_headers,
    get_admin_headers_with_project,
    get_user_headers,
    get_tenant_a_headers,
    get_tenant_b_headers,
)

# 兼容旧代码的变量名
ADMIN_API_KEY = ADMIN["api_key"]
TEST_PROJECT_ID = TENANT_A["code"]


# 兼容旧代码
def get_auth_headers() -> dict:
    """获取认证头（默认管理员）"""
    return get_admin_headers()


# ============================================================
# Fixtures - 管理员模式客户端
# ============================================================

@pytest.fixture(scope="session")
def auth_headers() -> dict:
    """管理员认证头 fixture"""
    return get_admin_headers()


@pytest.fixture(scope="session")
def memory_client() -> Generator[httpx.Client, None, None]:
    """Memory 服务 HTTP 客户端（管理员模式）"""
    with httpx.Client(
        base_url=MEMORY_SERVICE_URL, 
        timeout=30.0,
        headers=get_admin_headers(),
    ) as client:
        yield client


@pytest.fixture(scope="session")
def knowledge_client() -> Generator[httpx.Client, None, None]:
    """Knowledge 服务 HTTP 客户端（管理员模式）"""
    with httpx.Client(
        base_url=KNOWLEDGE_SERVICE_URL, 
        timeout=30.0,
        headers=get_admin_headers(),
    ) as client:
        yield client


@pytest.fixture(scope="session")
def agent_client() -> Generator[httpx.Client, None, None]:
    """Agent 服务 HTTP 客户端（管理员模式）"""
    with httpx.Client(
        base_url=AGENT_SERVICE_URL, 
        timeout=60.0,
        headers=get_admin_headers(),
    ) as client:
        yield client


# ============================================================
# Fixtures - 工程模式客户端（带 project_id）
# ============================================================

@pytest.fixture(scope="session")
def memory_client_project() -> Generator[httpx.Client, None, None]:
    """Memory 服务 HTTP 客户端（工程模式，带 project_id）"""
    with httpx.Client(
        base_url=MEMORY_SERVICE_URL, 
        timeout=30.0,
        headers=get_tenant_a_headers(),
    ) as client:
        yield client


@pytest.fixture(scope="session")
def knowledge_client_project() -> Generator[httpx.Client, None, None]:
    """Knowledge 服务 HTTP 客户端（工程模式，带 project_id）"""
    with httpx.Client(
        base_url=KNOWLEDGE_SERVICE_URL, 
        timeout=30.0,
        headers=get_tenant_a_headers(),
    ) as client:
        yield client


@pytest.fixture(scope="session")
def agent_client_project() -> Generator[httpx.Client, None, None]:
    """Agent 服务 HTTP 客户端（工程模式，带 project_id）"""
    with httpx.Client(
        base_url=AGENT_SERVICE_URL, 
        timeout=60.0,
        headers=get_tenant_a_headers(),
    ) as client:
        yield client


# ============================================================
# Fixtures - 测试数据
# ============================================================

@pytest.fixture
def test_user_id() -> str:
    """测试用户 ID"""
    return TEST_USER_1["user_id"]


@pytest.fixture
def test_project_id() -> str:
    """测试项目 ID（使用 DAOYOUTEST）"""
    return TEST_PROJECT_ID


@pytest.fixture
def test_session_id() -> str:
    """测试会话 ID"""
    return "test_session_001"


@pytest.fixture
def admin_api_key() -> str:
    """管理员 API Key"""
    return ADMIN_API_KEY
