from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, BigInteger, Index
from sqlalchemy.orm import relationship
import bcrypt
from . import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False)
    phone = Column(String(11), nullable=True)  # 允许为空，支持纯微信登录
    password_hash = Column(String(60), nullable=True)  # 允许为空，支持纯微信登录
    
    # 主要微信信息（保留，用于向后兼容和主要身份标识）
    openid = Column(String(100), nullable=True)  # 主要微信openid
    unionid = Column(String(100), nullable=True)  # 主要微信unionid
    wechat_nickname = Column(String(100), nullable=True)  # 主要微信昵称
    wechat_avatar = Column(String(500), nullable=True)  # 主要微信头像
    
    # 推荐者关系
    referrer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)   # 推荐者ID
    is_referrer = Column(Boolean, default=False)  # 是否为推荐者
    
    # 时间字段
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    referrer = relationship("User", remote_side=[id], backref="referrals")
    
    # 微信账号关联关系（从表，存储所有关联的微信账号）
    wechat_accounts = relationship("WechatAccount", back_populates="user", cascade="all, delete-orphan")

    # 创建唯一索引
    __table_args__ = (
        Index('idx_phone_unique', 'phone', unique=True, postgresql_where=phone.isnot(None)),
        Index('idx_unionid_unique', 'unionid', unique=True, postgresql_where=unionid.isnot(None)),
        Index('idx_openid_unique', 'openid', unique=True, postgresql_where=openid.isnot(None)),
    )

    def set_password(self, password: str) -> None:
        """设置密码，自动进行哈希处理"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str) -> bool:
        """验证密码"""
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'openid': self.openid,
            'unionid': self.unionid,
            'wechat_nickname': self.wechat_nickname,
            'wechat_avatar': self.wechat_avatar,
            'referrer_id': self.referrer_id,
            'is_referrer': self.is_referrer,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            # 从微信账号关联获取所有微信账号信息
            'wechat_accounts': self.get_wechat_accounts()
        }
    
    def get_wechat_accounts(self) -> list:
        """获取所有关联的微信账号"""
        return [account.to_dict() for account in self.wechat_accounts]
    
    def has_wechat_account(self, wechat_type: str = None) -> bool:
        """检查是否有指定类型的微信账号"""
        if wechat_type:
            return any(account.wechat_type == wechat_type for account in self.wechat_accounts)
        return len(self.wechat_accounts) > 0
    
    def get_primary_wechat_info(self) -> dict:
        """获取主要的微信信息（从主表字段）"""
        return {
            'openid': self.openid,
            'unionid': self.unionid,
            'wechat_nickname': self.wechat_nickname,
            'wechat_avatar': self.wechat_avatar
        }
    
    def update_primary_wechat_info(self, openid: str = None, unionid: str = None, 
                                  wechat_nickname: str = None, wechat_avatar: str = None):
        """更新主要的微信信息"""
        if openid is not None:
            self.openid = openid
        if unionid is not None:
            self.unionid = unionid
        if wechat_nickname is not None:
            self.wechat_nickname = wechat_nickname
        if wechat_avatar is not None:
            self.wechat_avatar = wechat_avatar
        self.updated_at = datetime.utcnow() 