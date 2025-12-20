from fastapi import APIRouter, Query, Body, Depends, HTTPException
from typing import List, Optional, Any
from ..services.cache_service import CacheService
from ..models.cache_schemas import CacheFileListResponse, CacheFileDetailResponse, ChatMessage
import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..services.auth_service import user_service
from sqlalchemy.orm import Session
from redis import Redis
from ..core.database import get_db

router = APIRouter(tags=["Cache"])

logger = logging.getLogger(__name__)

security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    user = user_service.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="无效的认证凭据")
    return user.id

def get_redis():
    # 这里假设你有统一的redis连接管理
    import redis
    from os import getenv
    return redis.Redis.from_url(getenv("REDIS_URL", "redis://localhost:6379/0"))

# 获取会话列表
@router.get("/session-list")
def list_sessions(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    service_type: Optional[str] = Query(None),
    main_type: Optional[str] = Query(None)
):
    return CacheService.get_session_list(db, user_id, service_type, main_type)

# 获取会话详情
@router.get("/session-detail")
def session_detail(
    db: Session = Depends(get_db),
    session_id: str = Query(...)
):
    return CacheService.get_session_detail(db, session_id)

# 获取聊天历史
@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    session_id: str = Query(...),
    limit: int = Query(50)
):
    return CacheService.get_history(redis, db, session_id, limit)

# 保存消息
@router.post("/save-message")
def save_message(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    session_id: str = Body(...),
    user_id: int = Body(...),
    role: str = Body(...),
    content: str = Body(...),
    content_rag: Optional[str] = Body(None),
    order_num: int = Body(...),
    message_time: str = Body(...)
):
    from datetime import datetime
    CacheService.save_message(
        db, redis, session_id, user_id, role, content, content_rag, order_num, datetime.fromisoformat(message_time)
    )
    return {"success": True}

# 删除会话历史
@router.delete("/delete-history")
def delete_history(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    session_id: str = Query(...)
):
    CacheService.delete_history(redis, db, session_id)
    return {"success": True}
