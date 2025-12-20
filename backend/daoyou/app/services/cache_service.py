import json
from typing import List, Any, Optional, Dict
from fastapi import HTTPException
from sqlalchemy.orm import Session
from redis import Redis
from datetime import datetime
from ..models.cache_schemas import (
    CacheFileListResponse,
    CacheFileDetailResponse,
    ChatMessage
)
import logging
import os

logger = logging.getLogger(__name__)

class CacheService:
    @staticmethod
    def get_session_key(user_id: str, service_type: str, main_type: str, session_id: str) -> str:
        return f"chat:{user_id}:{service_type}:{main_type}:{session_id}"

    @staticmethod
    def save_message(db: Session, redis: Redis, session_id: str, user_id: str, role: str, content: str, content_rag: Optional[str], order_num: int, message_time: datetime):
        # 1. 写入数据库（仅新表）
        from ..models.conversation_message import ConversationMessage
        from ..models.conversation_session import ConversationSession

        try:
            project_id = os.getenv("MEMRAG_PROJECT_ID", "my_chat_app")

            # 确保会话头存在
            conv_session = db.query(ConversationSession).filter_by(session_id=str(session_id)).first()
            if conv_session is None:
                conv_session = ConversationSession(
                    session_id=str(session_id),
                    user_id=str(user_id) if user_id is not None else None,
                    project_id=project_id,
                )
                db.add(conv_session)

            # 写入消息记录
            conv_msg = ConversationMessage(
                session_id=str(session_id),
                user_id=str(user_id) if user_id is not None else None,
                agent_id=getattr(conv_session, "agent_id", None),
                project_id=project_id,
                role=role,
                content=content,
                extra_metadata={
                    "contentRAG": content_rag,
                    "order": order_num,
                },
            )
            db.add(conv_msg)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"save_message commit failed: {e}", exc_info=True)
            raise
        
        # 3. 写入redis（仅在DB提交成功后）
        cache_key = f"chat:{session_id}"
        redis.rpush(cache_key, json.dumps({
            "role": role,
            "content": content,
            "contentRAG": content_rag,
            "order": order_num,
            "timestamp": message_time.isoformat()
        }))
        redis.expire(cache_key, 86400)

    @staticmethod
    def get_history(redis: Redis, db: Session, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        cache_key = f"chat:{session_id}"
        history = redis.lrange(cache_key, 0, -1)
        if history:
            return [json.loads(x) for x in history]
        
        # 缓存没有，从数据库查
        from ..models.conversation_message import ConversationMessage
        from ..models.conversation_session import ConversationSession

        conv_session = db.query(ConversationSession).filter_by(session_id=session_id).first()
        if not conv_session:
            return []

        records: List[Any] = (
            db.query(ConversationMessage)
            .filter_by(session_id=session_id)
            .order_by(ConversationMessage.created_at, ConversationMessage.id)
            .limit(limit)
            .all()
        )

        for r in records:
            meta = r.extra_metadata or {}
            content_rag = meta.get("contentRAG") or meta.get("content_rag")
            order_val = meta.get("order") or meta.get("order_num")
            order_num = int(order_val) if order_val is not None else int(r.id)
            timestamp = r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat()

            redis.rpush(cache_key, json.dumps({
                "role": r.role,
                "content": r.content,
                "contentRAG": content_rag,
                "order": order_num,
                "timestamp": timestamp,
            }))
        redis.expire(cache_key, 86400)

        result: List[Dict[str, Any]] = []
        for r in records:
            meta = r.extra_metadata or {}
            content_rag = meta.get("contentRAG") or meta.get("content_rag")
            order_val = meta.get("order") or meta.get("order_num")
            order_num = int(order_val) if order_val is not None else int(r.id)
            timestamp = r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat()

            result.append({
                "role": r.role,
                "content": r.content,
                "contentRAG": content_rag,
                "order": order_num,
                "timestamp": timestamp,
            })

        return result

    @staticmethod
    def delete_history(redis: Redis, db: Session, session_id: str):
        # 删除数据库记录
        from ..models.conversation_message import ConversationMessage
        from ..models.conversation_session import ConversationSession

        db.query(ConversationMessage).filter_by(session_id=session_id).delete()
        db.query(ConversationSession).filter_by(session_id=session_id).delete()

        db.commit()
        
        # 删除redis缓存
        cache_key = f"chat:{session_id}"
        redis.delete(cache_key)

    @staticmethod
    def set_intent_json(redis: Redis, session_id: str, service_type: str, intent_json: Dict[str, Any], ttl_seconds: int = 86400):
        try:
            key = f"intent:{service_type}:{session_id}"
            redis.setex(key, ttl_seconds, json.dumps(intent_json, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"set_intent_json failed: {e}")

    @staticmethod
    def get_intent_json(redis: Redis, session_id: str, service_type: str) -> Optional[Dict[str, Any]]:
        try:
            key = f"intent:{service_type}:{session_id}"
            val = redis.get(key)
            if not val:
                return None
            data = json.loads(val)
            return data if isinstance(data, dict) else None
        except Exception as e:
            logger.warning(f"get_intent_json failed: {e}")
            return None

    @staticmethod
    def set_retrieval_cache(
        redis: Redis,
        session_id: str,
        service_type: str,
        key_hash: str,
        payload: Dict[str, Any],
        ttl_seconds: int = 1800
    ) -> None:
        try:
            key = f"retrieval:{service_type}:{session_id}:{key_hash}"
            redis.setex(key, ttl_seconds, json.dumps(payload, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"set_retrieval_cache failed: {e}")

    @staticmethod
    def get_retrieval_cache(
        redis: Redis,
        session_id: str,
        service_type: str,
        key_hash: str
    ) -> Optional[Dict[str, Any]]:
        try:
            key = f"retrieval:{service_type}:{session_id}:{key_hash}"
            val = redis.get(key)
            if not val:
                return None
            data = json.loads(val)
            return data if isinstance(data, dict) else None
        except Exception as e:
            logger.warning(f"get_retrieval_cache failed: {e}")
            return None

    @staticmethod
    def get_session_list(db: Session, user_id: str, service_type: Optional[str] = None, main_type: Optional[str] = None) -> List[Dict[str, Any]]:
        from ..models.conversation_session import ConversationSession
        from ..models.conversation_message import ConversationMessage
        from ..models.conversation_message import ConversationMessage

        # 首先尝试从新会话表（conversation_sessions）获取列表
        project_id = os.getenv("MEMRAG_PROJECT_ID", "my_chat_app")
        conv_query = db.query(ConversationSession).filter_by(
            user_id=str(user_id),
            project_id=project_id,
        )
        if service_type:
            conv_query = conv_query.filter_by(agent_id=service_type)

        conv_sessions = conv_query.order_by(ConversationSession.created_at.desc()).all()

        if not conv_sessions:
            return []

        # 为每个会话获取第一条消息，用于生成会话名称
        session_ids = [s.session_id for s in conv_sessions if s.session_id]
        first_msg_map: Dict[str, Any] = {}
        if session_ids:
            msgs = (
                db.query(ConversationMessage)
                .filter(ConversationMessage.session_id.in_(session_ids))
                .order_by(ConversationMessage.session_id, ConversationMessage.created_at, ConversationMessage.id)
                .all()
            )
            for m in msgs:
                sid = m.session_id
                if sid not in first_msg_map and m.content:
                    first_msg_map[sid] = m

        # 使用新表返回会话列表，字段名保持与旧接口兼容
        result: List[Dict[str, Any]] = []
        for s in conv_sessions:
            raw_title = None
            first_msg = first_msg_map.get(s.session_id)
            if first_msg and first_msg.content:
                text = str(first_msg.content).strip()
                if text:
                    raw_title = text[:20] + "…"

            if not raw_title:
                raw_title = getattr(s, "title", None) or s.session_id

            result.append({
                "session_id": s.session_id,
                "service_type": getattr(s, "agent_id", None) or (service_type or "unknown"),
                "main_type": main_type or "chatcache",
                "session_name": raw_title,
                "created_at": s.created_at.isoformat() if getattr(s, "created_at", None) else None,
                "updated_at": (s.closed_at or s.created_at).isoformat() if getattr(s, "created_at", None) else None,
                "last_message": "",
                "message_count": 0,
                "summary": "",
            })

        return result

    @staticmethod
    def get_session_detail(db: Session, session_id: str) -> Optional[Dict[str, Any]]:
        from ..models.conversation_session import ConversationSession
        from ..models.conversation_message import ConversationMessage

        # 从新会话/消息表读取详情
        conv_session = db.query(ConversationSession).filter_by(session_id=session_id).first()
        if conv_session is not None:
            messages = (
                db.query(ConversationMessage)
                .filter_by(session_id=session_id)
                .order_by(ConversationMessage.created_at, ConversationMessage.id)
                .all()
            )
            message_list = []
            for m in messages:
                meta = m.extra_metadata or {}
                content_rag = meta.get("contentRAG") or meta.get("content_rag")
                order_val = meta.get("order") or meta.get("order_num")
                order_num = int(order_val) if order_val is not None else int(m.id)
                timestamp = m.created_at.isoformat() if m.created_at else datetime.utcnow().isoformat()
                message_list.append({
                    "role": m.role,
                    "content": m.content,
                    "content_rag": content_rag,
                    "order": order_num,
                    "timestamp": timestamp,
                })

            return {
                "session_id": conv_session.session_id,
                "service_type": getattr(conv_session, "agent_id", None),
                "main_type": "chatcache",
                "session_name": getattr(conv_session, "title", None) or conv_session.session_id,
                "created_at": conv_session.created_at.isoformat() if getattr(conv_session, "created_at", None) else None,
                "summary": "",
                "messages": message_list,
            }
        return None
