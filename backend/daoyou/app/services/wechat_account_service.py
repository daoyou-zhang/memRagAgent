from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..models.wechat_account import WechatAccount
from ..models.user import User

import logging
from datetime import datetime
import uuid

# 创建logger实例
logger = logging.getLogger(__name__)

class WechatAccountService:
    """微信账号服务"""
    
    def __init__(self):
        pass
    
    def create_wechat_account(
        self, 
        user_id: str, 
        openid: str, 
        wechat_type: str, 
        unionid: Optional[str] = None,
        wechat_nickname: Optional[str] = None,
        wechat_avatar: Optional[str] = None,
        db: Session = None
    ) -> WechatAccount:
        """创建微信账号关联"""
        try:
            wechat_account = WechatAccount(
                id=str(uuid.uuid4()),
                user_id=user_id,
                openid=openid,
                unionid=unionid,
                wechat_type=wechat_type,
                wechat_nickname=wechat_nickname,
                wechat_avatar=wechat_avatar,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(wechat_account)
            db.commit()
            db.refresh(wechat_account)
            
            return wechat_account
            
        except Exception as e:
            db.rollback()
            logger.error(f"创建微信账号关联失败: {str(e)}")
            raise
    
    def find_user_by_openid(self, openid: str, db: Session) -> Optional[User]:
        """通过openid查找用户"""
        try:
            wechat_account = db.query(WechatAccount).filter(
                WechatAccount.openid == openid
            ).first()
            
            if wechat_account:
                user = db.query(User).filter(User.id == wechat_account.user_id).first()
                if user:
                    # 将user的openid设置为wechat_account的openid，确保数据一致性
                    user.openid = wechat_account.openid
                    user.unionid = wechat_account.unionid
                    user.wechat_nickname = wechat_account.wechat_nickname
                    user.wechat_avatar = wechat_account.wechat_avatar
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"通过openid查找用户失败: {str(e)}")
            return None
    
    def find_user_by_unionid(self, unionid: str, db: Session) -> Optional[User]:
        """通过unionid查找用户"""
        try:
            wechat_account = db.query(WechatAccount).filter(
                WechatAccount.unionid == unionid
            ).first()
            
            if wechat_account:
                user = db.query(User).filter(User.id == wechat_account.user_id).first()
                if user:
                    # 将user的openid设置为wechat_account的openid，确保数据一致性
                    user.openid = wechat_account.openid
                    user.unionid = wechat_account.unionid
                    user.wechat_nickname = wechat_account.wechat_nickname
                    user.wechat_avatar = wechat_account.wechat_avatar
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"通过unionid查找用户失败: {str(e)}")
            return None
    
    def find_user_by_wechat_identity(self, wechat_data: dict, db: Session) -> Optional[User]:
        """根据微信身份信息查找用户，优先使用unionid"""
        try:
            # 优先通过unionid查找
            if wechat_data.get("unionid"):
                user = self.find_user_by_unionid(wechat_data["unionid"], db)
                if user:
                    return user
            
            # 如果没有unionid，使用openid查找
            if wechat_data.get("openid"):
                user = self.find_user_by_openid(wechat_data["openid"], db)
                if user:
                    return user
            
            return None
            
        except Exception as e:
            logger.error(f"查找微信用户失败: {str(e)}")
            return None
    
    def link_wechat_to_existing_user(
        self, 
        openid: str, 
        wechat_type: str, 
        existing_user_id: str,
        unionid: Optional[str] = None,
        wechat_nickname: Optional[str] = None,
        wechat_avatar: Optional[str] = None,
        db: Session = None
    ) -> WechatAccount:
        """将微信账号关联到已存在的用户"""
        try:
            # 检查是否已有该openid的关联
            existing_account = db.query(WechatAccount).filter(
                WechatAccount.openid == openid
            ).first()
            
            if existing_account:
                # 更新现有关联
                existing_account.user_id = existing_user_id
                existing_account.unionid = unionid or existing_account.unionid
                existing_account.wechat_nickname = wechat_nickname or existing_account.wechat_nickname
                existing_account.wechat_avatar = wechat_avatar or existing_account.wechat_avatar
                existing_account.updated_at = datetime.utcnow()
                
                db.commit()
                return existing_account
            else:
                # 创建新关联
                return self.create_wechat_account(
                    user_id=existing_user_id,
                    openid=openid,
                    wechat_type=wechat_type,
                    unionid=unionid,
                    wechat_nickname=wechat_nickname,
                    wechat_avatar=wechat_avatar,
                    db=db
                )
                
        except Exception as e:
            logger.error(f"关联微信账号到现有用户失败: {str(e)}")
            raise
    
    def get_user_wechat_accounts(self, user_id: str, db: Session) -> List[WechatAccount]:
        """获取用户的所有微信账号"""
        try:
            return db.query(WechatAccount).filter(
                WechatAccount.user_id == user_id
            ).all()
            
        except Exception as e:
            logger.error(f"获取用户微信账号失败: {str(e)}")
            return []
    
    def remove_wechat_account(self, openid: str, db: Session) -> bool:
        """移除微信账号关联"""
        try:
            wechat_account = db.query(WechatAccount).filter(
                WechatAccount.openid == openid
            ).first()
            
            if wechat_account:
                db.delete(wechat_account)
                db.commit()
                return True
            
            return False
            
        except Exception as e:
            db.rollback()
            logger.error(f"移除微信账号关联失败: {str(e)}")
            return False

# 创建服务实例
wechat_account_service = WechatAccountService() 