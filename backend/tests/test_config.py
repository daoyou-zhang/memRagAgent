"""测试配置文件

集中管理测试用户、API Key 和工程信息。
修改此文件后，需确保数据库中的数据与此配置一致。

数据库同步指南：
1. 管理员账户 - 使用 .env 中的 ADMIN_API_KEY
2. 测试租户 - 需在 tenants 表中创建
3. 测试用户 - 需在 tenant_users 表中创建
4. API Keys - 需在 api_keys 表中创建
"""
import os

# ============================================================
# 服务地址
# ============================================================
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", "http://127.0.0.1:5000")
KNOWLEDGE_SERVICE_URL = os.getenv("KNOWLEDGE_SERVICE_URL", "http://127.0.0.1:5001")
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://127.0.0.1:8000")


# ============================================================
# 管理员配置（最高权限，可访问所有数据）
# ============================================================
ADMIN = {
    "api_key": os.getenv("ADMIN_API_KEY", "15948640987Zhy~"),
    "description": "超级管理员，可访问所有租户的所有数据",
}


# ============================================================
# 测试租户配置
# ============================================================
# 租户 A - 主要测试用
TENANT_A = {
    "id": 10,
    "code": "DAOYOUTEST",
    "name": "道友测试GM",
}

# 租户 B - 用于隔离测试
TENANT_B = {
    "id": 11,
    "code": "TENANT_B",
    "name": "道友测试GM02",
}


# ============================================================
# 测试用户配置
# ============================================================
# 用户 1 - 属于租户 A，有完整权限
TEST_USER_1 = {
    "user_id": "3",
    "username": "道友GM用户01",
    "tenant_id": TENANT_A["id"],
    "project_id": TENANT_A["code"],
    "api_key": "sk-M4qnWcqY4gloOCn0LFdYSRg_JdBOjjijfPOcYiW13Qk",  # 需要在数据库创建后填入
    "role": "admin",
    "scopes": ["*"],
}

# 用户 2 - 属于租户 A，只读权限
TEST_USER_2 = {
    "user_id": "4",
    "username": "道友GM用户02",
    "tenant_id": TENANT_A["id"],
    "project_id": TENANT_A["code"],
    "api_key": "sk-IYK-Jzmi3lVKNmINpbbUhL07K7kTlYwH7JS1ouUwfwc",
    "role": "viewer",
    "scopes": ["read:memories", "read:knowledge"],
}

# 用户 3 - 属于租户 B，用于隔离测试
TEST_USER_3 = {
    "user_id": "6",
    "username": "道友GM02用户02",
    "tenant_id": TENANT_B["id"],
    "project_id": TENANT_B["code"],
    "api_key": "sk-6mHwcrCub-GFEnAsOTTg9NMGF07DnEK9-ijukPZbL5A",
    "role": "member",
    "scopes": ["read:memories", "write:memories"],
}


# ============================================================
# 测试会话
# ============================================================
TEST_SESSIONS = {
    "session_1": "test_session_001",
    "session_2": "test_session_002",
}


# ============================================================
# 便捷方法
# ============================================================

def get_admin_headers() -> dict:
    """获取管理员认证头"""
    return {"X-API-Key": ADMIN["api_key"]}


def get_admin_headers_with_project(project_id: str) -> dict:
    """获取管理员认证头 + 指定工程"""
    return {
        "X-API-Key": ADMIN["api_key"],
        "X-Project-Id": project_id,
    }


def get_user_headers(user: dict) -> dict:
    """获取用户认证头"""
    headers = {}
    if user.get("api_key"):
        headers["X-API-Key"] = user["api_key"]
    if user.get("project_id"):
        headers["X-Project-Id"] = user["project_id"]
    if user.get("user_id"):
        headers["X-User-Id"] = user["user_id"]
    return headers


def get_tenant_a_headers() -> dict:
    """获取租户 A 的认证头（使用租户 A 用户的 API Key）"""
    return {
        "X-API-Key": TEST_USER_1["api_key"],
        "X-Project-Id": TENANT_A["code"],
    }


def get_tenant_b_headers() -> dict:
    """获取租户 B 的认证头（使用租户 B 用户的 API Key）"""
    return {
        "X-API-Key": TEST_USER_3["api_key"],
        "X-Project-Id": TENANT_B["code"],
    }


# ============================================================
# 数据库同步说明
# ============================================================
"""
测试数据通过前端 /tenants 页面创建，步骤：

1. 创建租户
   - 名称：道友测试GM / 道友测试GM02
   - 编码：DAOYOUTEST / TENANT_B

2. 创建用户
   - 在租户详情中添加用户
   - 设置角色：admin / member / viewer

3. 创建 API Key
   - 在租户详情中创建 API Key
   - 复制密钥到上面的配置中

注意：API Key 只在创建时显示一次，如果丢失需要重新生成。
"""
