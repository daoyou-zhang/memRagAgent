from fastapi import APIRouter
from .auth import router as auth_router
from .defaultai_chat_new import router as chat_new_router
from .websocket import router as websocket_router
from .cache import router as cache_router
from .reward import router as reward_router
from .referrer import router as referrer_router
from .service_types import router as service_types_router
from .support import router as support_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(chat_new_router)  # 已在模块内声明 prefix="/chat"
router.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
router.include_router(cache_router, prefix="/cache", tags=["缓存"])
router.include_router(reward_router, prefix="/reward", tags=["打赏"])
router.include_router(referrer_router, prefix="/referrer", tags=["推荐者"])
router.include_router(service_types_router, tags=["服务类型"])
router.include_router(support_router, prefix="/support", tags=["support"])

__all__ = [
    "router",
    "auth_router",
    "chat_new_router",
    "websocket_router",
    "cache_router",
    "reward_router",
    "referrer_router",
    "service_types_router",
    "support_router",
]