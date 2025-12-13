"""多租户模型

支持多租户、用户组、用户角色的数据模型。

架构：
- Tenant: 租户（顶层隔离单位）
- UserGroup: 用户组（属于租户）
- User: 用户（属于用户组）
- Role: 角色（权限控制）
"""
from datetime import datetime
from typing import Optional, Any, List

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from repository.db_session import Base


class Tenant(Base):
    """租户

    顶层隔离单位，所有数据按 tenant_id 隔离。
    """

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 租户标识（唯一）
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # 租户名称
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # 租户类型：personal（个人）, team（团队）, enterprise（企业）
    type: Mapped[str] = mapped_column(String(32), default="personal")
    
    # 状态：active, suspended, deleted
    status: Mapped[str] = mapped_column(String(32), default="active")
    
    # 配置（JSON）
    config: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    
    # 配额限制
    max_users: Mapped[int] = mapped_column(Integer, default=10)
    max_storage_mb: Mapped[int] = mapped_column(Integer, default=1000)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # 关系
    user_groups: Mapped[List["UserGroup"]] = relationship(
        "UserGroup", back_populates="tenant", cascade="all, delete-orphan"
    )
    users: Mapped[List["TenantUser"]] = relationship(
        "TenantUser", back_populates="tenant", cascade="all, delete-orphan"
    )


class UserGroup(Base):
    """用户组

    属于租户，用于组织用户。
    """

    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 所属租户
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # 组标识（租户内唯一）
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # 组名称
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # 描述
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 是否为默认组
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 组配置
    config: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # 关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="user_groups")
    users: Mapped[List["TenantUser"]] = relationship(
        "TenantUser", back_populates="user_group", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_user_group_tenant_code"),
        Index("ix_user_group_tenant_default", "tenant_id", "is_default"),
    )


class TenantUser(Base):
    """租户用户

    memRag 系统用户，属于租户和用户组。
    表名 tenant_users 避免与其他项目 users 表冲突。
    """

    __tablename__ = "tenant_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 所属租户
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # 所属用户组（可选）
    group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user_groups.id", ondelete="SET NULL"), nullable=True
    )
    
    # 用户标识（全局唯一，用于登录）
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    
    # 邮箱（全局唯一）
    email: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True)
    
    # 显示名称
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # 密码哈希（如果使用密码认证）
    password_hash: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    
    # 外部 ID（用于对接外部系统）
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    
    # 角色：admin（管理员）, member（普通成员）, viewer（只读）
    role: Mapped[str] = mapped_column(String(32), default="member")
    
    # 状态：active, inactive, suspended
    status: Mapped[str] = mapped_column(String(32), default="active")
    
    # 用户配置
    config: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    
    # 最后登录时间
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # 关系
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    user_group: Mapped[Optional["UserGroup"]] = relationship("UserGroup", back_populates="users")
    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_user_tenant_role", "tenant_id", "role"),
        Index("ix_user_external", "tenant_id", "external_id"),
    )


class ApiKey(Base):
    """API 密钥

    用于 API 认证，关联到用户或租户。
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 所属租户
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # 关联用户（可选，为空表示租户级密钥）
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tenant_users.id", ondelete="CASCADE"), nullable=True
    )
    
    # 关系
    user: Mapped[Optional["TenantUser"]] = relationship("TenantUser", back_populates="api_keys")
    
    # 密钥名称
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # 密钥前缀（用于识别，如 "sk-xxx"）
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    
    # 密钥哈希（存储哈希值，不存明文）
    key_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    
    # 权限范围（JSON 数组）
    scopes: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(32), default="active")
    
    # 过期时间
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 最后使用时间
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_api_key_tenant_user", "tenant_id", "user_id"),
    )
