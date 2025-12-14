"""租户服务

提供租户、用户组、用户的管理功能。
"""
import hashlib
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy.orm import Session

from models.tenant import Tenant, UserGroup, TenantUser, ApiKey


class TenantService:
    """租户服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ========== 租户管理 ==========
    
    def create_tenant(
        self,
        code: str,
        name: str,
        tenant_type: str = "personal",
        max_users: int = 10,
        max_storage_mb: int = 1000,
        config: Dict = None,
    ) -> Tenant:
        """创建租户"""
        tenant = Tenant(
            code=code,
            name=name,
            type=tenant_type,
            status="active",
            max_users=max_users,
            max_storage_mb=max_storage_mb,
            config=config,
        )
        self.db.add(tenant)
        self.db.flush()
        
        # 创建默认用户组
        default_group = UserGroup(
            tenant_id=tenant.id,
            code="default",
            name="默认组",
            is_default=True,
        )
        self.db.add(default_group)
        self.db.flush()
        
        return tenant
    
    def get_tenant_by_code(self, code: str) -> Optional[Tenant]:
        """根据 code 获取租户"""
        return self.db.query(Tenant).filter(Tenant.code == code).first()
    
    def get_tenant_by_id(self, tenant_id: int) -> Optional[Tenant]:
        """根据 ID 获取租户"""
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    def list_tenants(
        self,
        status: str = None,
        tenant_type: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Tenant]:
        """列出租户"""
        q = self.db.query(Tenant)
        if status:
            q = q.filter(Tenant.status == status)
        if tenant_type:
            q = q.filter(Tenant.type == tenant_type)
        return q.order_by(Tenant.created_at.desc()).offset(offset).limit(limit).all()
    
    def update_tenant(
        self,
        tenant_id: int,
        name: str = None,
        status: str = None,
        config: Dict = None,
        max_users: int = None,
        max_storage_mb: int = None,
    ) -> Optional[Tenant]:
        """更新租户"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        if name is not None:
            tenant.name = name
        if status is not None:
            tenant.status = status
        if config is not None:
            tenant.config = config
        if max_users is not None:
            tenant.max_users = max_users
        if max_storage_mb is not None:
            tenant.max_storage_mb = max_storage_mb
        
        self.db.flush()
        return tenant
    
    def delete_tenant(self, tenant_id: int) -> bool:
        """删除租户（级联删除所有关联数据）"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False
        
        self.db.delete(tenant)
        return True
    
    # ========== 用户组管理 ==========
    
    def create_user_group(
        self,
        tenant_id: int,
        code: str,
        name: str,
        description: str = None,
        is_default: bool = False,
        config: Dict = None,
    ) -> UserGroup:
        """创建用户组"""
        # 如果设为默认组，先取消其他默认组
        if is_default:
            self.db.query(UserGroup).filter(
                UserGroup.tenant_id == tenant_id,
                UserGroup.is_default == True,
            ).update({"is_default": False})
        
        group = UserGroup(
            tenant_id=tenant_id,
            code=code,
            name=name,
            description=description,
            is_default=is_default,
            config=config,
        )
        self.db.add(group)
        self.db.flush()
        return group
    
    def get_user_group(self, tenant_id: int, code: str) -> Optional[UserGroup]:
        """获取用户组"""
        return self.db.query(UserGroup).filter(
            UserGroup.tenant_id == tenant_id,
            UserGroup.code == code,
        ).first()
    
    def get_default_group(self, tenant_id: int) -> Optional[UserGroup]:
        """获取默认用户组"""
        return self.db.query(UserGroup).filter(
            UserGroup.tenant_id == tenant_id,
            UserGroup.is_default == True,
        ).first()
    
    def list_user_groups(self, tenant_id: int) -> List[UserGroup]:
        """列出租户下的所有用户组"""
        return self.db.query(UserGroup).filter(
            UserGroup.tenant_id == tenant_id
        ).order_by(UserGroup.created_at.asc()).all()
    
    # ========== 用户管理 ==========
    
    def create_user(
        self,
        tenant_id: int,
        username: str,
        email: str = None,
        display_name: str = None,
        password: str = None,
        external_id: str = None,
        role: str = "member",
        group_id: int = None,
        config: Dict = None,
    ) -> TenantUser:
        """创建用户"""
        # 如果没有指定组，使用默认组
        if group_id is None:
            default_group = self.get_default_group(tenant_id)
            if default_group:
                group_id = default_group.id
        
        # 密码哈希
        password_hash = None
        if password:
            password_hash = self._hash_password(password)
        
        user = TenantUser(
            tenant_id=tenant_id,
            group_id=group_id,
            username=username,
            email=email,
            display_name=display_name or username,
            password_hash=password_hash,
            external_id=external_id,
            role=role,
            status="active",
            config=config,
        )
        self.db.add(user)
        self.db.flush()
        return user
    
    def get_user_by_username(self, username: str) -> Optional[TenantUser]:
        """根据用户名获取用户"""
        return self.db.query(TenantUser).filter(TenantUser.username == username).first()
    
    def get_user_by_email(self, email: str) -> Optional[TenantUser]:
        """根据邮箱获取用户"""
        return self.db.query(TenantUser).filter(TenantUser.email == email).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[TenantUser]:
        """根据 ID 获取用户"""
        return self.db.query(TenantUser).filter(TenantUser.id == user_id).first()
    
    def get_user_by_external_id(self, tenant_id: int, external_id: str) -> Optional[TenantUser]:
        """根据外部 ID 获取用户"""
        return self.db.query(TenantUser).filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.external_id == external_id,
        ).first()
    
    def list_users(
        self,
        tenant_id: int,
        group_id: int = None,
        role: str = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TenantUser]:
        """列出租户下的用户"""
        q = self.db.query(TenantUser).filter(TenantUser.tenant_id == tenant_id)
        if group_id is not None:
            q = q.filter(TenantUser.group_id == group_id)
        if role:
            q = q.filter(TenantUser.role == role)
        if status:
            q = q.filter(TenantUser.status == status)
        return q.order_by(TenantUser.created_at.desc()).offset(offset).limit(limit).all()
    
    def update_user(
        self,
        user_id: int,
        display_name: str = None,
        email: str = None,
        role: str = None,
        status: str = None,
        group_id: int = None,
        config: Dict = None,
    ) -> Optional[TenantUser]:
        """更新用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        if display_name is not None:
            user.display_name = display_name
        if email is not None:
            user.email = email
        if role is not None:
            user.role = role
        if status is not None:
            user.status = status
        if group_id is not None:
            user.group_id = group_id
        if config is not None:
            user.config = config
        
        self.db.flush()
        return user
    
    def verify_password(self, user: TenantUser, password: str) -> bool:
        """验证密码"""
        if not user.password_hash or not password:
            return False
        return self._hash_password(password) == user.password_hash
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """更新密码"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        user.password_hash = self._hash_password(new_password)
        return True
    
    def record_login(self, user_id: int) -> None:
        """记录登录时间"""
        user = self.get_user_by_id(user_id)
        if user:
            user.last_login_at = datetime.now()
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
        self.db.delete(user)
        self.db.flush()
        return True
    
    # ========== API 密钥管理 ==========
    
    def create_api_key(
        self,
        tenant_id: int,
        name: str,
        user_id: int = None,
        scopes: List[str] = None,
        expires_at: datetime = None,
    ) -> Tuple[ApiKey, str]:
        """创建 API 密钥
        
        Returns:
            (ApiKey, 明文密钥) - 明文密钥只返回一次
        """
        # 生成密钥
        raw_key = secrets.token_urlsafe(32)
        key_prefix = f"sk-{raw_key[:8]}"
        key_hash = self._hash_api_key(raw_key)
        
        api_key = ApiKey(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes,
            status="active",
            expires_at=expires_at,
        )
        self.db.add(api_key)
        self.db.flush()
        
        # 返回完整密钥（只返回一次）
        full_key = f"sk-{raw_key}"
        return api_key, full_key
    
    def verify_api_key(self, key: str) -> Optional[ApiKey]:
        """验证 API 密钥"""
        if not key or not key.startswith("sk-"):
            return None
        
        # 去掉前缀
        raw_key = key[3:]
        key_hash = self._hash_api_key(raw_key)
        
        api_key = self.db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash,
            ApiKey.status == "active",
        ).first()
        
        if api_key:
            # 检查过期
            if api_key.expires_at and api_key.expires_at < datetime.now():
                return None
            
            # 更新使用时间
            api_key.last_used_at = datetime.now()
        
        return api_key
    
    def revoke_api_key(self, key_id: int) -> bool:
        """撤销 API 密钥"""
        api_key = self.db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if not api_key:
            return False
        api_key.status = "revoked"
        return True
    
    def list_api_keys(
        self,
        tenant_id: int,
        user_id: int = None,
    ) -> List[ApiKey]:
        """列出 API 密钥"""
        q = self.db.query(ApiKey).filter(ApiKey.tenant_id == tenant_id)
        if user_id is not None:
            q = q.filter(ApiKey.user_id == user_id)
        return q.order_by(ApiKey.created_at.desc()).all()
    
    # ========== 辅助方法 ==========
    
    def _hash_password(self, password: str) -> str:
        """密码哈希（简单实现，生产环境应使用 bcrypt）"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _hash_api_key(self, key: str) -> str:
        """API 密钥哈希"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    # ========== 统计 ==========
    
    def get_tenant_stats(self, tenant_id: int) -> Dict[str, Any]:
        """获取租户统计信息"""
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            return {}
        
        user_count = self.db.query(TenantUser).filter(TenantUser.tenant_id == tenant_id).count()
        group_count = self.db.query(UserGroup).filter(UserGroup.tenant_id == tenant_id).count()
        api_key_count = self.db.query(ApiKey).filter(
            ApiKey.tenant_id == tenant_id,
            ApiKey.status == "active",
        ).count()
        
        return {
            "tenant_id": tenant_id,
            "tenant_code": tenant.code,
            "tenant_name": tenant.name,
            "user_count": user_count,
            "group_count": group_count,
            "api_key_count": api_key_count,
            "max_users": tenant.max_users,
            "usage_percent": round(user_count / tenant.max_users * 100, 1) if tenant.max_users > 0 else 0,
        }
