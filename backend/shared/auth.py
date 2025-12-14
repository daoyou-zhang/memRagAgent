"""认证中间件

提供 API 认证和权限控制：
- API Key 认证
- 租户隔离
- 角色权限
"""
import os
from functools import wraps
from typing import Optional, Tuple, List

from loguru import logger

# 环境变量配置
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "sk-admin-secret-key")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"


class AuthContext:
    """认证上下文"""
    
    def __init__(
        self,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        role: str = "anonymous",
        scopes: List[str] = None,
        is_admin: bool = False,
    ):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role
        self.scopes = scopes or []
        self.is_admin = is_admin
    
    def can_access_tenant(self, tenant_id: int) -> bool:
        """检查是否可以访问指定租户"""
        if self.is_admin:
            return True
        return self.tenant_id == tenant_id
    
    def has_scope(self, scope: str) -> bool:
        """检查是否有指定权限"""
        if self.is_admin:
            return True
        return scope in self.scopes or "*" in self.scopes
    
    def has_role(self, required_role: str) -> bool:
        """检查角色权限"""
        if self.is_admin:
            return True
        role_hierarchy = {"viewer": 0, "member": 1, "admin": 2}
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)


def get_api_key_from_request(request) -> Optional[str]:
    """从 Flask 请求中提取 API Key"""
    # 1. 从 Header 获取
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    # 2. 从 X-API-Key Header 获取
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    # 3. 从 Query 参数获取（不推荐，仅用于调试）
    api_key = request.args.get("api_key")
    if api_key:
        return api_key
    
    return None


def get_api_key_from_fastapi_request(request) -> Optional[str]:
    """从 FastAPI 请求中提取 API Key"""
    # 1. 从 Header 获取
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    # 2. 从 X-API-Key Header 获取
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    # 3. 从 Query 参数获取（不推荐，仅用于调试）
    api_key = request.query_params.get("api_key")
    if api_key:
        return api_key
    
    return None


def verify_api_key_with_db(api_key: str, db_session) -> Tuple[bool, Optional[AuthContext]]:
    """通过数据库验证 API Key
    
    Returns:
        (is_valid, auth_context)
    """
    from memory.services.tenant_service import TenantService
    
    svc = TenantService(db_session)
    key_record = svc.verify_api_key(api_key)
    
    if not key_record:
        return False, None
    
    # 构建认证上下文
    ctx = AuthContext(
        tenant_id=key_record.tenant_id,
        user_id=key_record.user_id,
        role=key_record.user.role if key_record.user else "member",
        scopes=key_record.scopes or [],
        is_admin=False,
    )
    
    return True, ctx


def verify_admin_key(api_key: str) -> Tuple[bool, Optional[AuthContext]]:
    """验证管理员密钥"""
    if api_key == ADMIN_API_KEY:
        return True, AuthContext(is_admin=True, role="admin")
    return False, None


# ============================================================
# Flask 中间件 (Memory/Knowledge 服务)
# ============================================================

def _extract_tenant_context(request) -> dict:
    """从 Flask 请求中提取租户上下文
    
    优先级：Header > Body > Query
    """
    tenant_id = None
    project_id = None
    user_id = None
    
    # 从 Header 获取
    tenant_id = request.headers.get("X-Tenant-Id")
    project_id = request.headers.get("X-Project-Id")
    user_id = request.headers.get("X-User-Id")
    
    # 从 Body 获取（如果 Header 没有）
    if request.is_json:
        body = request.get_json(silent=True) or {}
        tenant_id = tenant_id or body.get("tenant_id")
        project_id = project_id or body.get("project_id")
        user_id = user_id or body.get("user_id")
    
    # 从 Query 获取
    tenant_id = tenant_id or request.args.get("tenant_id")
    project_id = project_id or request.args.get("project_id")
    user_id = user_id or request.args.get("user_id")
    
    return {
        "tenant_id": int(tenant_id) if tenant_id and str(tenant_id).isdigit() else None,
        "project_id": project_id,
        "user_id": user_id,
    }


def apply_project_filter(query, model, project_id: str = None):
    """为查询添加 project_id 过滤
    
    规则：
    - 若显式提供了 project_id（参数或 Header 上下文），则无论是否管理员都按该 project_id 过滤
    - 否则：管理员不过滤，普通用户不带 project_id 时也不滤（向后兼容）
    """
    from flask import g

    # 解析有效的 project_id（参数优先，其次上下文）
    effective_pid = project_id
    if effective_pid is None:
        ctx = getattr(g, "tenant_ctx", {}) or {}
        effective_pid = ctx.get("project_id")

    auth = getattr(g, "auth", None)

    # 如果明确指定了 project_id，则强制过滤（即便管理员）
    if effective_pid:
        if hasattr(model, "project_id"):
            return query.filter(model.project_id == effective_pid)
        return query

    # 没有指定 project_id：管理员不过滤；普通用户按旧逻辑不滤
    if auth and getattr(auth, "is_admin", False):
        return query

    return query


def flask_auth_required(scopes: List[str] = None, roles: List[str] = None):
    """Flask 路由认证装饰器
    
    功能：
    1. 验证 API Key
    2. 设置 g.auth (AuthContext)
    3. 设置 g.tenant_ctx (租户上下文)
    
    用法:
        @flask_auth_required(scopes=["read:memories"])
        def get_memories():
            # g.auth.is_admin 判断是否管理员
            # g.tenant_ctx 获取租户上下文
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify, g
            
            # 提取租户上下文（无论认证是否启用都要提取）
            tenant_ctx = _extract_tenant_context(request)
            g.tenant_ctx = tenant_ctx
            
            # 如果认证未启用，跳过检查，授予管理员权限
            if not AUTH_ENABLED:
                g.auth = AuthContext(is_admin=True)
                return f(*args, **kwargs)
            
            api_key = get_api_key_from_request(request)
            
            if not api_key:
                return jsonify({"error": "API key required", "code": "AUTH_REQUIRED"}), 401
            
            # 1. 检查管理员密钥
            is_admin, admin_ctx = verify_admin_key(api_key)
            if is_admin:
                g.auth = admin_ctx
                return f(*args, **kwargs)
            
            # 2. 检查数据库密钥
            db = SessionLocal()
            try:
                is_valid, auth_ctx = verify_api_key_with_db(api_key, db)
                
                if not is_valid:
                    return jsonify({"error": "Invalid API key", "code": "INVALID_KEY"}), 401
                
                # 检查权限范围
                if scopes:
                    for scope in scopes:
                        if not auth_ctx.has_scope(scope):
                            return jsonify({
                                "error": f"Missing scope: {scope}",
                                "code": "INSUFFICIENT_SCOPE"
                            }), 403
                
                # 检查角色
                if roles:
                    has_required_role = any(auth_ctx.has_role(r) for r in roles)
                    if not has_required_role:
                        return jsonify({
                            "error": f"Required role: {roles}",
                            "code": "INSUFFICIENT_ROLE"
                        }), 403
                
                g.auth = auth_ctx
                return f(*args, **kwargs)
                
            finally:
                db.close()
        
        return decorated_function
    return decorator


def flask_tenant_filter():
    """获取当前请求的租户过滤条件
    
    用法:
        tenant_id = flask_tenant_filter()
        query = query.filter(Memory.tenant_id == tenant_id)
    """
    from flask import g
    
    auth: AuthContext = getattr(g, "auth", None)
    if not auth:
        return None
    
    if auth.is_admin:
        return None  # 管理员可以访问所有租户
    
    return auth.tenant_id


# ============================================================
# FastAPI 中间件 (daoyou_agent 服务)
# ============================================================

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

# FastAPI 安全方案
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def get_api_key_fastapi(
    api_key_header: str = Security(api_key_header),
    api_key_query: str = Security(api_key_query),
) -> Optional[str]:
    """从 FastAPI 请求中提取 API Key"""
    return api_key_header or api_key_query


async def fastapi_auth(
    request: Request,
    api_key: str = Security(api_key_header),
) -> AuthContext:
    """FastAPI 认证依赖
    
    用法:
        @router.get("/")
        async def endpoint(auth: AuthContext = Depends(fastapi_auth)):
            if not auth.is_admin:
                raise HTTPException(403, "Admin only")
    """
    if not AUTH_ENABLED:
        return AuthContext(is_admin=True)
    
    # 从多个来源获取 API Key
    key = api_key
    if not key:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            key = auth_header[7:]
    if not key:
        key = request.query_params.get("api_key")
    
    if not key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # 检查管理员密钥
    is_admin, admin_ctx = verify_admin_key(key)
    if is_admin:
        return admin_ctx
    
    # 数据库验证（同步，因为 daoyou_agent 用同步 DB）
    try:
        from daoyou_agent.repository.db_session import SessionLocal
        db = SessionLocal()
        try:
            is_valid, auth_ctx = verify_api_key_with_db(key, db)
            if is_valid:
                return auth_ctx
        finally:
            db.close()
    except ImportError:
        pass  # 如果导入失败，继续尝试其他方式
    
    raise HTTPException(status_code=401, detail="Invalid API key")


async def fastapi_auth_optional(
    request: Request,
    api_key: str = Security(api_key_header),
) -> AuthContext:
    """可选认证（不强制要求 API Key）"""
    if not AUTH_ENABLED:
        return AuthContext(is_admin=True)
    
    try:
        return await fastapi_auth(request, api_key)
    except HTTPException:
        return AuthContext()  # 匿名用户


def require_admin(auth: AuthContext) -> None:
    """要求管理员权限"""
    if not auth.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")


def require_scope(auth: AuthContext, scope: str) -> None:
    """要求指定权限"""
    if not auth.has_scope(scope):
        raise HTTPException(status_code=403, detail=f"Missing scope: {scope}")


def require_tenant_access(auth: AuthContext, tenant_id: int) -> None:
    """要求租户访问权限"""
    if not auth.can_access_tenant(tenant_id):
        raise HTTPException(status_code=403, detail="Cannot access this tenant")


# ============================================================
# 权限范围定义
# ============================================================

class Scopes:
    """权限范围常量"""
    
    # 记忆
    READ_MEMORIES = "read:memories"
    WRITE_MEMORIES = "write:memories"
    DELETE_MEMORIES = "delete:memories"
    
    # 知识库
    READ_KNOWLEDGE = "read:knowledge"
    WRITE_KNOWLEDGE = "write:knowledge"
    DELETE_KNOWLEDGE = "delete:knowledge"
    
    # 用户画像
    READ_PROFILES = "read:profiles"
    WRITE_PROFILES = "write:profiles"
    
    # 认知服务
    USE_COGNITIVE = "use:cognitive"
    
    # 租户管理
    MANAGE_TENANTS = "manage:tenants"
    MANAGE_USERS = "manage:users"
    MANAGE_KEYS = "manage:keys"
    
    # 通配符
    ALL = "*"
