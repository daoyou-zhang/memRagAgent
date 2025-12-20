from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import os

from ..core.database import get_db
from sqlalchemy import or_
from ..services.auth_service import AuthService
from ..models.chat_message import ChatMessage
from ..models.chat_session import ChatSession
from ..models.user import User

router = APIRouter(tags=["统计"])
security = HTTPBearer()
auth_service = AuthService()


def _estimate_tokens(text: Optional[str]) -> int:
    if not text:
        return 0
    s = str(text)
    # 尝试使用 tiktoken 更精确估算；失败则用字符数/2 近似
    try:
        import tiktoken  # type: ignore
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(s))
    except Exception:
        return max(1, int(len(s) / 2))


@router.get("/token-usage")
def get_token_usage(
    session_id: Optional[str] = Query(default=None, description="会话ID (UUID)"),
    phone: Optional[str] = Query(default=None, description="手机号"),
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """按 session_id 或手机号统计 token 近似值。
    规则：user 统计 content_rag；assistant 统计 content；其余忽略。
    权限：仅允许手机号等于 TOKEN_STATS_PHONE（默认 15948640987）的用户访问。
    """
    # 认证与权限
    current_user = auth_service.get_user_by_token(credentials.credentials, db_session=db)
    if not current_user:
        raise HTTPException(status_code=401, detail="未认证")
    allowed_phone = os.getenv("TOKEN_STATS_PHONE", "15948640987")
    if str(current_user.phone or "") != str(allowed_phone):
        raise HTTPException(status_code=403, detail="无权限访问该统计页面")

    if not session_id and not phone:
        raise HTTPException(status_code=400, detail="必须提供 session_id 或 phone 之一")

    session_ids: List[str] = []
    target: Dict[str, Any] = {}

    if session_id:
        session_ids = [session_id]
        target["by"] = "session_id"
        target["value"] = session_id
    else:
        # 通过手机号查用户 -> 会话列表
        user_row = db.query(User).filter(User.phone == phone).first()
        if not user_row:
            return {"by": "phone", "value": phone, "total_tokens": 0, "assistant_tokens": 0, "user_tokens": 0, "sessions": []}
        sessions = db.query(ChatSession).filter(ChatSession.user_id == user_row.id).all()
        session_ids = [str(s.session_id) for s in sessions]
        target["by"] = "phone"
        target["value"] = phone

    if not session_ids:
        return {**target, "total_tokens": 0, "assistant_tokens": 0, "user_tokens": 0, "sessions": []}

    # 拉取消息并累计
    q = db.query(ChatMessage).filter(
        ChatMessage.session_id.in_(session_ids),
        or_(ChatMessage.is_deleted.is_(False), ChatMessage.is_deleted.is_(None))
    )
    rows: List[ChatMessage] = q.all()
    user_tokens = 0
    assistant_tokens = 0
    for m in rows:
        try:
            if m.role == "user":
                user_tokens += _estimate_tokens(m.content_rag if m.content_rag else m.content)
            elif m.role == "assistant":
                assistant_tokens += _estimate_tokens(m.content)
        except Exception:
            continue
    total = user_tokens + assistant_tokens

    # 可选：分会话小计（便于前端展示）
    per_session: Dict[str, Dict[str, int]] = {}
    for m in rows:
        sid = str(m.session_id)
        if sid not in per_session:
            per_session[sid] = {"user_tokens": 0, "assistant_tokens": 0, "total_tokens": 0}
        try:
            if m.role == "user":
                per_session[sid]["user_tokens"] += _estimate_tokens(m.content_rag if m.content_rag else m.content)
            elif m.role == "assistant":
                per_session[sid]["assistant_tokens"] += _estimate_tokens(m.content)
        except Exception:
            pass
    for sid, v in per_session.items():
        v["total_tokens"] = v["user_tokens"] + v["assistant_tokens"]

    return {
        **target,
        "total_tokens": total,
        "assistant_tokens": assistant_tokens,
        "user_tokens": user_tokens,
        "session_count": len(set(session_ids)),
        "message_count": len(rows),
        "sessions": [{"session_id": sid, **vals} for sid, vals in per_session.items()],
    }


