from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from sqlalchemy.orm import Session
from ..services.auth_service import user_service
from ..core.database import get_db
from ..models.user import User
from datetime import datetime

router = APIRouter(tags=["referrer"])
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    user = user_service.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="无效的认证凭据")
    return user.id

@router.get("/my-referrer")
async def get_my_referrer(current_user_id: str = Depends(get_current_user_id)):
    """获取我的推荐者信息"""
    try:
        current_user = user_service.get_user_by_id(current_user_id)
        if not current_user or not current_user.referrer_id:
            return {"success": True, "data": None, "message": "暂无推荐者"}
        
        referrer = user_service.get_user_by_id(current_user.referrer_id)
        if not referrer:
            return {"success": True, "data": None, "message": "推荐者信息不存在"}
        
        return {
            "success": True,
            "data": {
                "id": referrer.id,
                "name": referrer.username,
                "phone": referrer.phone,
                "wechat_nickname": referrer.wechat_nickname
            },
            "message": "获取成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐者信息失败: {str(e)}")

@router.get("/my-referrals")
async def get_my_referrals(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """获取我推荐的用户列表"""
    try:
        # 使用SQLite数据库查询被推荐用户
        referrals = db.query(User).filter(User.referrer_id == current_user_id).all()
        
        referral_list = [
            {
                "id": user.id,
                "name": user.name,
                "phone": user.phone,
                "wechat_nickname": user.wechat_nickname,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in referrals
        ]
        
        return {
            "success": True,
            "data": {
                "referrals": referral_list,
                "total": len(referral_list)
            },
            "message": "获取成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐用户列表失败: {str(e)}")

@router.post("/bind-referrer")
async def bind_referrer(
    referrer_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """绑定推荐者"""
    try:
        # 检查推荐者是否存在（支持手机号或id）
        referrer = user_service.get_user_by_id_or_phone(referrer_id)
        if not referrer:
            raise HTTPException(status_code=400, detail="推荐者不存在")
        
        # 检查是否已经是推荐者
        if referrer_id == current_user_id:
            raise HTTPException(status_code=400, detail="不能推荐自己")
        
        # 检查当前用户是否已有推荐者
        current_user = user_service.get_user_by_id(current_user_id)
        if current_user and current_user.referrer_id:
            raise HTTPException(status_code=400, detail="已有推荐者，无法重复绑定")
        
        # 更新用户的推荐者ID
        user = db.query(User).filter(User.id == current_user_id).first()
        if user:
            user.referrer_id = referrer_id
            user.updated_at = datetime.utcnow()
            db.commit()
        
        return {
            "success": True,
            "message": "推荐者绑定成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"绑定推荐者失败: {str(e)}")

@router.get("/referrer-link/{user_id}")
async def get_referrer_link(user_id: str):
    """获取推荐链接"""
    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=400, detail="用户不存在")
        
        # 生成推荐链接
        # 这里可以根据实际需求生成不同类型的链接
        web_link = f"https://your-domain.com/register?referrer={user_id}"
        miniprogram_link = f"pages/register/register?referrer={user_id}"
        
        return {
            "success": True,
            "data": {
                "user_id": user_id,
                "user_name": user.username,
                "web_link": web_link,
                "miniprogram_link": miniprogram_link
            },
            "message": "获取成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取推荐链接失败: {str(e)}") 