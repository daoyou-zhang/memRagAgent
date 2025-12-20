from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..services.auth_service import user_service
from ..models.auth_schemas import UserInfo

security = HTTPBearer()

async def get_current_user(request: Request) -> UserInfo:
    """获取当前用户"""
    credentials: HTTPAuthorizationCredentials = await security(request)
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="未提供认证信息"
        )

    user = user_service.get_user_by_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="无效的认证信息"
        )

    return user 