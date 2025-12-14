"""租户上下文管理

确保所有数据操作都有租户/项目隔离
"""
import os
from typing import Optional
from functools import wraps
from flask import request, jsonify, g

# 是否强制要求 project_id（生产环境应为 true）
REQUIRE_PROJECT_ID = os.getenv("REQUIRE_PROJECT_ID", "false").lower() == "true"


def get_request_context() -> dict:
    """从请求中提取租户上下文
    
    优先级：
    1. Header: X-Tenant-Id, X-Project-Id
    2. Body: tenant_id, project_id
    3. Query: tenant_id, project_id
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


def require_project_context(f):
    """装饰器：要求请求必须有 project_id
    
    用法:
        @require_project_context
        def my_route():
            ctx = g.tenant_ctx
            project_id = ctx["project_id"]  # 保证有值
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        ctx = get_request_context()
        
        if REQUIRE_PROJECT_ID and not ctx["project_id"]:
            return jsonify({
                "error": "project_id is required",
                "hint": "Pass via Header (X-Project-Id) or Body (project_id)"
            }), 400
        
        g.tenant_ctx = ctx
        return f(*args, **kwargs)
    
    return decorated


def apply_tenant_filter(query, model, ctx: dict = None):
    """为 SQLAlchemy 查询添加租户过滤
    
    用法:
        query = db.query(Memory)
        query = apply_tenant_filter(query, Memory, g.tenant_ctx)
    
    Args:
        query: SQLAlchemy 查询对象
        model: 模型类（需要有 tenant_id 或 project_id 字段）
        ctx: 租户上下文，默认从 g.tenant_ctx 获取
    """
    if ctx is None:
        ctx = getattr(g, "tenant_ctx", {}) or {}
    
    # 管理员不过滤
    auth = getattr(g, "auth", None)
    if auth and getattr(auth, "is_admin", False):
        return query
    
    # 按 tenant_id 过滤
    tenant_id = ctx.get("tenant_id")
    if tenant_id and hasattr(model, "tenant_id"):
        query = query.filter(model.tenant_id == tenant_id)
    
    # 按 project_id 过滤
    project_id = ctx.get("project_id")
    if project_id and hasattr(model, "project_id"):
        query = query.filter(model.project_id == project_id)
    
    return query


def get_tenant_values(ctx: dict = None) -> dict:
    """获取用于创建记录的租户字段值
    
    用法:
        mem = Memory(
            text="xxx",
            **get_tenant_values()  # 自动填充 tenant_id, project_id, user_id
        )
    """
    if ctx is None:
        ctx = getattr(g, "tenant_ctx", {}) or {}
    
    return {
        "tenant_id": ctx.get("tenant_id"),
        "project_id": ctx.get("project_id"),
        "user_id": ctx.get("user_id"),
    }
