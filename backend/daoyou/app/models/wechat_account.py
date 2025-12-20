from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base  # 从models包导入Base
import uuid

class WechatAccount(Base):
    """微信账号关联表"""
    __tablename__ = "wechat_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    openid = Column(String(64), unique=True, nullable=False, index=True)
    unionid = Column(String(64), index=True)
    wechat_type = Column(String(20), nullable=False, index=True)  # miniprogram/mp/website
    wechat_nickname = Column(String(100))
    wechat_avatar = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    user = relationship("User", back_populates="wechat_accounts")
    
    def __repr__(self):
        return f"<WechatAccount(id={self.id}, openid={self.openid}, wechat_type={self.wechat_type})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "openid": self.openid,
            "unionid": self.unionid,
            "wechat_type": self.wechat_type,
            "wechat_nickname": self.wechat_nickname,
            "wechat_avatar": self.wechat_avatar,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        } 