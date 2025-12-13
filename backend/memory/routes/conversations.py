"""对话记录 API

接收完整对话数据，由 memory 服务统一处理：
- 存储原始对话
- 生成 episodic/semantic 记忆
- 触发画像聚合
"""
from datetime import datetime
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session

from repository.db_session import SessionLocal
from models.memory import Memory, ConversationMessage, ConversationSession, MemoryGenerationJob
from llm_client import UNIFIED_MEMORY_GENERATION

conversations_bp = Blueprint("conversations", __name__)


@conversations_bp.post("/record")
def record_conversation():
    """记录完整对话（由调用方在对话结束后调用）
    
    请求体:
    {
        "user_id": "xxx",
        "session_id": "yyy",
        "project_id": "zzz",
        
        "raw_query": "用户原始输入",
        "optimized_query": "RAG优化后的查询（可选）",
        
        "intent": {
            "category": "divination",
            "confidence": 0.95,
            "needs_tool": true
        },
        
        "tool_used": "bazi_paipan",
        "tool_result": "工具返回结果摘要",
        
        "context_used": {
            "profile_summary": "用户画像摘要",
            "memory_count": 5,
            "rag_count": 3
        },
        
        "llm_response": "LLM 最终回复",
        "processing_time": 3.5,
        
        "auto_generate_memory": true
    }
    """
    data = request.get_json() or {}
    
    user_id = data.get("user_id")
    session_id = data.get("session_id")
    project_id = data.get("project_id")
    
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400
    
    raw_query = data.get("raw_query", "")
    optimized_query = data.get("optimized_query")
    intent = data.get("intent", {})
    tool_used = data.get("tool_used")
    tool_result = data.get("tool_result")
    context_used = data.get("context_used", {})
    llm_response = data.get("llm_response", "")
    processing_time = data.get("processing_time", 0)
    auto_generate = data.get("auto_generate_memory", True)
    
    db: Session = SessionLocal()
    try:
        # 1. 确保 session 存在
        session = db.query(ConversationSession).filter(
            ConversationSession.session_id == session_id
        ).first()
        
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
            }
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
                "tool_result_summary": str(tool_result)[:500] if tool_result else None,
                "context_used": context_used,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
            }
        )
        db.add(assistant_msg)
        db.flush()
        
        # 4. 如果启用自动记忆生成，创建 Job
        job_id = None
        if auto_generate and user_id:
            # 使用统一记忆生成（1 次 LLM）还是分开（2 次 LLM）
            job_type = "unified_memory" if UNIFIED_MEMORY_GENERATION else "episodic_summary"
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
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "user_message_id": user_msg.id,
            "assistant_message_id": assistant_msg.id,
            "memory_job_id": job_id,
            "message": "对话已记录，记忆生成任务已创建" if job_id else "对话已记录",
        })
        
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()  # 打印完整错误堆栈
        return jsonify({"error": str(e), "type": type(e).__name__}), 500
    finally:
        db.close()


@conversations_bp.get("/history/<session_id>")
def get_conversation_history(session_id: str):
    """获取会话历史"""
    limit = int(request.args.get("limit", 50))
    
    db: Session = SessionLocal()
    try:
        messages = db.query(ConversationMessage).filter(
            ConversationMessage.session_id == session_id
        ).order_by(ConversationMessage.created_at.asc()).limit(limit).all()
        
        return jsonify({
            "session_id": session_id,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "metadata": m.extra_metadata,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
            "count": len(messages),
        })
    finally:
        db.close()


@conversations_bp.get("/sessions")
def list_sessions():
    """获取会话列表"""
    user_id = request.args.get("user_id")
    project_id = request.args.get("project_id")
    limit = int(request.args.get("limit", 20))
    
    db: Session = SessionLocal()
    try:
        q = db.query(ConversationSession)
        if user_id:
            q = q.filter(ConversationSession.user_id == user_id)
        if project_id:
            q = q.filter(ConversationSession.project_id == project_id)
        
        sessions = q.order_by(ConversationSession.created_at.desc()).limit(limit).all()
        
        return jsonify({
            "sessions": [
                {
                    "id": s.id,
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "project_id": s.project_id,
                    "title": s.title,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in sessions
            ],
            "count": len(sessions),
        })
    finally:
        db.close()
