"""认证与租户隔离测试

测试场景：
1. AUTH_ENABLED=false（开发模式）- 所有请求都有管理员权限
2. AUTH_ENABLED=true（生产模式）- 需要有效 API Key
3. 管理员模式 - 使用 ADMIN_API_KEY，可访问所有数据
4. 工程模式 - 带 X-Project-Id，只能访问该工程的数据
5. 租户隔离 - 不同租户的数据相互隔离

运行方式：
    pytest tests/test_auth.py -v
    pytest tests/test_auth.py::TestAdminMode -v
    pytest tests/test_auth.py::TestAuthEnabled -v  # 需要 AUTH_ENABLED=true
"""
import os
import pytest
import httpx

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
    get_admin_headers,
    get_admin_headers_with_project,
    get_user_headers,
    get_tenant_a_headers,
    get_tenant_b_headers,
)

# 检测是否启用认证
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"


class TestAdminMode:
    """管理员模式测试"""

    def test_admin_can_access_memory_service(self, memory_client):
        """管理员可以访问 Memory 服务"""
        resp = memory_client.get("/api/memory/health")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    def test_admin_can_query_all_memories(self, memory_client):
        """管理员可以查询所有记忆（不带 project_id）"""
        resp = memory_client.post("/api/memory/memories/query", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_admin_can_access_knowledge_service(self, knowledge_client):
        """管理员可以访问 Knowledge 服务"""
        resp = knowledge_client.get("/api/knowledge/health")
        assert resp.status_code == 200

    def test_admin_can_list_all_collections(self, knowledge_client):
        """管理员可以列出所有知识集合（不带 project_id）"""
        resp = knowledge_client.get("/api/knowledge/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


class TestProjectMode:
    """工程模式测试"""

    def test_project_mode_query_memories(self, memory_client_project, test_project_id):
        """工程模式只能查询该工程的记忆"""
        resp = memory_client_project.post("/api/memory/memories/query", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        # 验证返回的记忆都属于该工程
        for item in data.get("items", []):
            mem = item.get("memory", {})
            # 如果有 project_id，应该匹配
            if mem.get("project_id"):
                assert mem["project_id"] == test_project_id, \
                    f"Expected project_id={test_project_id}, got {mem['project_id']}"

    def test_project_mode_list_collections(self, knowledge_client_project, test_project_id):
        """工程模式只能列出该工程的知识集合"""
        resp = knowledge_client_project.get("/api/knowledge/collections")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        # 验证返回的集合都属于该工程或为共享集合（project_id 为空）
        for col in data.get("items", []):
            pid = col.get("project_id")
            # 允许 project_id 为空（共享集合）或匹配当前工程
            assert pid is None or pid == "" or pid == test_project_id, \
                f"Expected project_id={test_project_id} or empty, got {pid}"


class TestTenantIsolation:
    """租户隔离测试"""

    def test_different_projects_are_isolated(self):
        """不同工程的数据相互隔离"""
        # 使用租户 A 的头
        headers_a = get_tenant_a_headers()
        # 使用租户 B 的头
        headers_b = get_tenant_b_headers()

        with httpx.Client(base_url=MEMORY_SERVICE_URL, timeout=30.0) as client:
            # 工程 A 查询
            resp_a = client.post(
                "/api/memory/memories/query",
                json={},
                headers=headers_a
            )
            assert resp_a.status_code == 200
            data_a = resp_a.json()

            # 工程 B 查询
            resp_b = client.post(
                "/api/memory/memories/query",
                json={},
                headers=headers_b
            )
            assert resp_b.status_code == 200
            data_b = resp_b.json()

            # 验证数据隔离（A 的数据中不应有 B 的 project_id）
            for item in data_a.get("items", []):
                mem = item.get("memory", {})
                if mem.get("project_id"):
                    assert mem["project_id"] != TENANT_B["code"], \
                        f"租户 A 的数据中不应有租户 B 的记录"

            for item in data_b.get("items", []):
                mem = item.get("memory", {})
                if mem.get("project_id"):
                    assert mem["project_id"] != TENANT_A["code"], \
                        f"租户 B 的数据中不应有租户 A 的记录"


class TestAuthDisabled:
    """AUTH_ENABLED=false 模式测试（开发模式）"""

    @pytest.mark.skipif(AUTH_ENABLED, reason="仅当 AUTH_ENABLED=false 时运行")
    def test_no_auth_still_works(self):
        """无认证也能访问（开发模式）"""
        with httpx.Client(base_url=MEMORY_SERVICE_URL, timeout=30.0) as client:
            resp = client.post("/api/memory/memories/query", json={})
            # 开发模式下应该返回 200
            assert resp.status_code == 200, f"开发模式下无需认证，但返回 {resp.status_code}"


class TestAuthEnabled:
    """AUTH_ENABLED=true 模式测试（生产模式）"""

    @pytest.mark.skipif(not AUTH_ENABLED, reason="仅当 AUTH_ENABLED=true 时运行")
    def test_no_auth_returns_401(self):
        """无认证返回 401"""
        with httpx.Client(base_url=MEMORY_SERVICE_URL, timeout=30.0) as client:
            resp = client.post("/api/memory/memories/query", json={})
            assert resp.status_code == 401, f"生产模式下无认证应返回 401，但返回 {resp.status_code}"

    @pytest.mark.skipif(not AUTH_ENABLED, reason="仅当 AUTH_ENABLED=true 时运行")
    def test_invalid_key_returns_401(self):
        """无效 API Key 返回 401"""
        with httpx.Client(
            base_url=MEMORY_SERVICE_URL,
            timeout=30.0,
            headers={"X-API-Key": "invalid-key-12345"}
        ) as client:
            resp = client.post("/api/memory/memories/query", json={})
            assert resp.status_code == 401, f"无效 Key 应返回 401，但返回 {resp.status_code}"

    @pytest.mark.skipif(not AUTH_ENABLED, reason="仅当 AUTH_ENABLED=true 时运行")
    def test_valid_admin_key_works(self):
        """有效管理员 Key 可以访问"""
        with httpx.Client(
            base_url=MEMORY_SERVICE_URL,
            timeout=30.0,
            headers=get_admin_headers()
        ) as client:
            resp = client.post("/api/memory/memories/query", json={})
            assert resp.status_code == 200, f"有效 Key 应返回 200，但返回 {resp.status_code}"


class TestUserRoles:
    """用户角色权限测试"""

    def test_user_1_config(self):
        """验证测试用户 1 配置"""
        assert TEST_USER_1["project_id"] == TENANT_A["code"]
        assert TEST_USER_1["role"] == "admin"
        assert TEST_USER_1["tenant_id"] == TENANT_A["id"]

    def test_user_2_config(self):
        """验证测试用户 2 配置"""
        assert TEST_USER_2["project_id"] == TENANT_A["code"]
        assert TEST_USER_2["role"] == "viewer"

    def test_user_3_isolated(self):
        """验证测试用户 3 属于不同租户"""
        assert TEST_USER_3["tenant_id"] == TENANT_B["id"]
        assert TEST_USER_3["project_id"] == TENANT_B["code"]
        assert TEST_USER_3["tenant_id"] != TEST_USER_1["tenant_id"]


class TestTenantManagement:
    """租户管理 API 测试"""

    def test_list_tenants(self, memory_client):
        """列出所有租户"""
        resp = memory_client.get("/api/tenants")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_get_tenant_users(self, memory_client):
        """获取租户用户列表"""
        resp = memory_client.get(f"/api/tenants/{TENANT_A['id']}/users")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_get_tenant_api_keys(self, memory_client):
        """获取租户 API Keys 列表"""
        resp = memory_client.get(f"/api/tenants/{TENANT_A['id']}/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    def test_get_tenant_groups(self, memory_client):
        """获取租户用户组列表"""
        resp = memory_client.get(f"/api/tenants/{TENANT_A['id']}/groups")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
