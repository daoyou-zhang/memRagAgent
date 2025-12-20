# memory/services/conversation_service.py
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..repository.db_session import SessionLocal
from ..models.memory import (
    Memory,
    ConversationMessage,
    ConversationSession,
    MemoryGenerationJob,
)
from ..llm_client import UNIFIED_MEMORY_GENERATION

def record_conversation_service(
    *,
    user_id: Optional[str],
    session_id: str,
    project_id: Optional[str],
    raw_query: str,
    optimized_query: Optional[str],
    intent: Dict[str, Any],
    tool_used: Optional[str],
    tool_result: Optional[str],
    context_used: Dict[str, Any],
    llm_response: str,
    processing_time: float,
    auto_generate: bool,
) -> Dict[str, Any]:
    db: Session = SessionLocal()
    try:
        # 1. 确保 session 存在
        session = (
            db.query(ConversationSession)
            .filter(ConversationSession.session_id == session_id)
            .first()
        )
        if not session:
            session = ConversationSession(
                session_id=session_id,
                user_id=user_id,
                project_id=project_id,
                status="active",
            )
            db.add(session)
            db.flush()

        # 2. 存储用户消息
        user_msg = ConversationMessage(
            session_id=session_id,
            user_id=user_id,
            project_id=project_id,
            role="user",
            content=raw_query,
            extra_metadata={
                "optimized_query": optimized_query,
                "intent": intent,
                "timestamp": datetime.now().isoformat(),
            },
        )
        db.add(user_msg)

        # 3. 存储助手消息
        assistant_msg = ConversationMessage(
            session_id=session_id,
            user_id=user_id,
            project_id=project_id,
            role="assistant",
            content=llm_response,
            extra_metadata={
                "tool_used": tool_used,
                "tool_result_summary": str(tool_result)[:500]
                if tool_result
                else None,
                "context_used": context_used,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
            },
        )
        db.add(assistant_msg)
        db.flush()

        # 4. 如果启用自动记忆生成，创建 Job
        job_id = None
        if auto_generate and user_id:
            job_type = (
                "unified_memory"
                if UNIFIED_MEMORY_GENERATION
                else "episodic_summary"
            )
            job = MemoryGenerationJob(
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
                start_message_id=user_msg.id,
                end_message_id=assistant_msg.id,
                job_type=job_type,
                target_types=["episodic", "semantic"],
                status="pending",
            )
            db.add(job)
            db.flush()
            job_id = job.id

        db.commit()
        return {
            "success": True,
            "session_id": session_id,
            "user_message_id": user_msg.id,
            "assistant_message_id": assistant_msg.id,
            "memory_job_id": job_id,
            "message": (
                "对话已记录，记忆生成任务已创建" if job_id else "对话已记录"
            ),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()