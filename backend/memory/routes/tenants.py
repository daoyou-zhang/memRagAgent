"""租户管理 API

提供租户、用户组、用户的 CRUD 接口。
"""
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session
from datetime import datetime
from zoneinfo import ZoneInfo

from repository.db_session import SessionLocal
from services.tenant_service import TenantService


tenants_bp = Blueprint("tenants", __name__)


def to_beijing_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("Asia/Shanghai")).isoformat()


# ============================================================
# 租户管理
# ============================================================

@tenants_bp.post("/tenants")
def create_tenant():
    """创建租户
    
    请求体：
    {
        "code": "tenant_code",
        "name": "租户名称",
        "type": "personal",  // personal/team/enterprise
        "max_users": 10,
        "max_storage_mb": 1000,
        "config": {}
    }
    """
    payload = request.get_json(force=True) or {}
    
    code = (payload.get("code") or "").strip()
    name = (payload.get("name") or "").strip()
    
    if not code or not name:
        return jsonify({"error": "code and name are required"}), 400
    
    tenant_type = payload.get("type", "personal")
    max_users = int(payload.get("max_users", 10))
    max_storage_mb = int(payload.get("max_storage_mb", 1000))
    config = payload.get("config")
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        
        # 检查 code 是否已存在
        if svc.get_tenant_by_code(code):
            return jsonify({"error": f"tenant code '{code}' already exists"}), 409
        
        tenant = svc.create_tenant(
            code=code,
            name=name,
            tenant_type=tenant_type,
            max_users=max_users,
            max_storage_mb=max_storage_mb,
            config=config,
        )
        db.commit()
        
        return jsonify({
            "id": tenant.id,
            "code": tenant.code,
            "name": tenant.name,
            "type": tenant.type,
            "status": tenant.status,
            "max_users": tenant.max_users,
            "max_storage_mb": tenant.max_storage_mb,
            "created_at": to_beijing_iso(tenant.created_at),
        }), 201
    finally:
        db.close()


@tenants_bp.get("/tenants")
def list_tenants():
    """列出租户"""
    status = request.args.get("status")
    tenant_type = request.args.get("type")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        tenants = svc.list_tenants(status, tenant_type, limit, offset)
        
        items = []
        for t in tenants:
            items.append({
                "id": t.id,
                "code": t.code,
                "name": t.name,
                "type": t.type,
                "status": t.status,
                "max_users": t.max_users,
                "created_at": to_beijing_iso(t.created_at),
            })
        
        return jsonify({"items": items, "count": len(items)})
    finally:
        db.close()


@tenants_bp.get("/tenants/<int:tenant_id>")
def get_tenant(tenant_id: int):
    """获取租户详情"""
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        tenant = svc.get_tenant_by_id(tenant_id)
        
        if not tenant:
            return jsonify({"error": "tenant not found"}), 404
        
        stats = svc.get_tenant_stats(tenant_id)
        
        return jsonify({
            "id": tenant.id,
            "code": tenant.code,
            "name": tenant.name,
            "type": tenant.type,
            "status": tenant.status,
            "config": tenant.config,
            "max_users": tenant.max_users,
            "max_storage_mb": tenant.max_storage_mb,
            "created_at": to_beijing_iso(tenant.created_at),
            "updated_at": to_beijing_iso(tenant.updated_at),
            "stats": stats,
        })
    finally:
        db.close()


@tenants_bp.put("/tenants/<int:tenant_id>")
def update_tenant(tenant_id: int):
    """更新租户"""
    payload = request.get_json(force=True) or {}
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        tenant = svc.update_tenant(
            tenant_id=tenant_id,
            name=payload.get("name"),
            status=payload.get("status"),
            config=payload.get("config"),
            max_users=payload.get("max_users"),
            max_storage_mb=payload.get("max_storage_mb"),
        )
        
        if not tenant:
            return jsonify({"error": "tenant not found"}), 404
        
        db.commit()
        
        return jsonify({
            "id": tenant.id,
            "code": tenant.code,
            "name": tenant.name,
            "status": tenant.status,
            "updated_at": to_beijing_iso(tenant.updated_at),
        })
    finally:
        db.close()


@tenants_bp.delete("/tenants/<int:tenant_id>")
def delete_tenant(tenant_id: int):
    """删除租户"""
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        success = svc.delete_tenant(tenant_id)
        
        if not success:
            return jsonify({"error": "tenant not found"}), 404
        
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


# ============================================================
# 用户组管理
# ============================================================

@tenants_bp.post("/tenants/<int:tenant_id>/groups")
def create_user_group(tenant_id: int):
    """创建用户组"""
    payload = request.get_json(force=True) or {}
    
    code = (payload.get("code") or "").strip()
    name = (payload.get("name") or "").strip()
    
    if not code or not name:
        return jsonify({"error": "code and name are required"}), 400
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        
        # 检查租户是否存在
        if not svc.get_tenant_by_id(tenant_id):
            return jsonify({"error": "tenant not found"}), 404
        
        # 检查组 code 是否已存在
        if svc.get_user_group(tenant_id, code):
            return jsonify({"error": f"group code '{code}' already exists"}), 409
        
        group = svc.create_user_group(
            tenant_id=tenant_id,
            code=code,
            name=name,
            description=payload.get("description"),
            is_default=bool(payload.get("is_default", False)),
            config=payload.get("config"),
        )
        db.commit()
        
        return jsonify({
            "id": group.id,
            "tenant_id": group.tenant_id,
            "code": group.code,
            "name": group.name,
            "is_default": group.is_default,
            "created_at": to_beijing_iso(group.created_at),
        }), 201
    finally:
        db.close()


@tenants_bp.get("/tenants/<int:tenant_id>/groups")
def list_user_groups(tenant_id: int):
    """列出用户组"""
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        groups = svc.list_user_groups(tenant_id)
        
        items = []
        for g in groups:
            items.append({
                "id": g.id,
                "code": g.code,
                "name": g.name,
                "description": g.description,
                "is_default": g.is_default,
                "created_at": to_beijing_iso(g.created_at),
            })
        
        return jsonify({"items": items, "count": len(items)})
    finally:
        db.close()


# ============================================================
# 用户管理
# ============================================================

@tenants_bp.post("/tenants/<int:tenant_id>/users")
def create_user(tenant_id: int):
    """创建用户
    
    请求体：
    {
        "username": "user1",
        "email": "user@example.com",
        "display_name": "用户1",
        "password": "xxx",  // 可选
        "external_id": "ext_123",  // 可选
        "role": "member",  // admin/member/viewer
        "group_id": 1  // 可选
    }
    """
    payload = request.get_json(force=True) or {}
    
    username = (payload.get("username") or "").strip()
    if not username:
        return jsonify({"error": "username is required"}), 400
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        
        # 检查租户是否存在
        if not svc.get_tenant_by_id(tenant_id):
            return jsonify({"error": "tenant not found"}), 404
        
        # 检查用户名是否已存在
        if svc.get_user_by_username(username):
            return jsonify({"error": f"username '{username}' already exists"}), 409
        
        # 检查邮箱是否已存在
        email = payload.get("email")
        if email and svc.get_user_by_email(email):
            return jsonify({"error": f"email '{email}' already exists"}), 409
        
        user = svc.create_user(
            tenant_id=tenant_id,
            username=username,
            email=email,
            display_name=payload.get("display_name"),
            password=payload.get("password"),
            external_id=payload.get("external_id"),
            role=payload.get("role", "member"),
            group_id=payload.get("group_id"),
            config=payload.get("config"),
        )
        db.commit()
        
        return jsonify({
            "id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "status": user.status,
            "created_at": to_beijing_iso(user.created_at),
        }), 201
    finally:
        db.close()


@tenants_bp.get("/tenants/<int:tenant_id>/users")
def list_users(tenant_id: int):
    """列出用户"""
    group_id = request.args.get("group_id", type=int)
    role = request.args.get("role")
    status = request.args.get("status")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        users = svc.list_users(tenant_id, group_id, role, status, limit, offset)
        
        items = []
        for u in users:
            items.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "display_name": u.display_name,
                "role": u.role,
                "status": u.status,
                "group_id": u.group_id,
                "last_login_at": to_beijing_iso(u.last_login_at),
                "created_at": to_beijing_iso(u.created_at),
            })
        
        return jsonify({"items": items, "count": len(items)})
    finally:
        db.close()


@tenants_bp.get("/users/<int:user_id>")
def get_user(user_id: int):
    """获取用户详情"""
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        user = svc.get_user_by_id(user_id)
        
        if not user:
            return jsonify({"error": "user not found"}), 404
        
        return jsonify({
            "id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "external_id": user.external_id,
            "role": user.role,
            "status": user.status,
            "group_id": user.group_id,
            "config": user.config,
            "last_login_at": to_beijing_iso(user.last_login_at),
            "created_at": to_beijing_iso(user.created_at),
            "updated_at": to_beijing_iso(user.updated_at),
        })
    finally:
        db.close()


@tenants_bp.put("/users/<int:user_id>")
def update_user(user_id: int):
    """更新用户"""
    payload = request.get_json(force=True) or {}
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        user = svc.update_user(
            user_id=user_id,
            display_name=payload.get("display_name"),
            email=payload.get("email"),
            role=payload.get("role"),
            status=payload.get("status"),
            group_id=payload.get("group_id"),
            config=payload.get("config"),
        )
        
        if not user:
            return jsonify({"error": "user not found"}), 404
        
        db.commit()
        
        return jsonify({
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "status": user.status,
            "updated_at": to_beijing_iso(user.updated_at),
        })
    finally:
        db.close()


# ============================================================
# API 密钥管理
# ============================================================

@tenants_bp.post("/tenants/<int:tenant_id>/api-keys")
def create_api_key(tenant_id: int):
    """创建 API 密钥
    
    请求体：
    {
        "name": "密钥名称",
        "user_id": 1,  // 可选，关联用户
        "scopes": ["read", "write"],  // 可选
        "expires_at": "2025-12-31T23:59:59"  // 可选
    }
    """
    payload = request.get_json(force=True) or {}
    
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    
    expires_at = None
    if payload.get("expires_at"):
        try:
            expires_at = datetime.fromisoformat(payload["expires_at"].replace("Z", ""))
        except Exception:
            pass
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        
        if not svc.get_tenant_by_id(tenant_id):
            return jsonify({"error": "tenant not found"}), 404
        
        api_key, full_key = svc.create_api_key(
            tenant_id=tenant_id,
            name=name,
            user_id=payload.get("user_id"),
            scopes=payload.get("scopes"),
            expires_at=expires_at,
        )
        db.commit()
        
        return jsonify({
            "id": api_key.id,
            "name": api_key.name,
            "key": full_key,  # 只返回一次！
            "key_prefix": api_key.key_prefix,
            "scopes": api_key.scopes,
            "expires_at": to_beijing_iso(api_key.expires_at),
            "created_at": to_beijing_iso(api_key.created_at),
            "warning": "请妥善保存密钥，此密钥只显示一次",
        }), 201
    finally:
        db.close()


@tenants_bp.get("/tenants/<int:tenant_id>/api-keys")
def list_api_keys(tenant_id: int):
    """列出 API 密钥"""
    user_id = request.args.get("user_id", type=int)
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        keys = svc.list_api_keys(tenant_id, user_id)
        
        items = []
        for k in keys:
            items.append({
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "user_id": k.user_id,
                "scopes": k.scopes,
                "status": k.status,
                "expires_at": to_beijing_iso(k.expires_at),
                "last_used_at": to_beijing_iso(k.last_used_at),
                "created_at": to_beijing_iso(k.created_at),
            })
        
        return jsonify({"items": items, "count": len(items)})
    finally:
        db.close()


@tenants_bp.delete("/api-keys/<int:key_id>")
def revoke_api_key(key_id: int):
    """撤销 API 密钥"""
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        success = svc.revoke_api_key(key_id)
        
        if not success:
            return jsonify({"error": "api key not found"}), 404
        
        db.commit()
        return jsonify({"success": True})
    finally:
        db.close()


# ============================================================
# 认证
# ============================================================

@tenants_bp.post("/auth/verify-key")
def verify_api_key():
    """验证 API 密钥
    
    请求体：
    {
        "key": "sk-xxx..."
    }
    """
    payload = request.get_json(force=True) or {}
    key = payload.get("key", "")
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        api_key = svc.verify_api_key(key)
        
        if not api_key:
            return jsonify({"valid": False, "error": "invalid or expired key"}), 401
        
        db.commit()  # 更新 last_used_at
        
        return jsonify({
            "valid": True,
            "tenant_id": api_key.tenant_id,
            "user_id": api_key.user_id,
            "scopes": api_key.scopes,
        })
    finally:
        db.close()


@tenants_bp.post("/auth/login")
def login():
    """用户登录
    
    请求体：
    {
        "username": "user1",
        "password": "xxx"
    }
    """
    payload = request.get_json(force=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")
    
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    
    db: Session = SessionLocal()
    try:
        svc = TenantService(db)
        user = svc.get_user_by_username(username)
        
        if not user or not svc.verify_password(user, password):
            return jsonify({"error": "invalid credentials"}), 401
        
        if user.status != "active":
            return jsonify({"error": "user is not active"}), 403
        
        svc.record_login(user.id)
        db.commit()
        
        return jsonify({
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
        })
    finally:
        db.close()
