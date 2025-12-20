"""知识洞察 API 路由

提供知识提取、查询、推送到知识库等功能
"""
import os
from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session

from ..repository.db_session import SessionLocal
from ..models.memory import Memory, KnowledgeInsight, SelfReflection
from ..llm_client import extract_knowledge_insights, generate_profile_with_reflection

knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.get("/insights")
def list_insights():
    """获取知识洞察列表"""
    project_id = request.args.get("project_id")
    category = request.args.get("category")
    status = request.args.get("status", "pending")
    limit = int(request.args.get("limit", 50))
    
    db: Session = SessionLocal()
    try:
        q = db.query(KnowledgeInsight)
        
        if project_id:
            q = q.filter(KnowledgeInsight.project_id == project_id)
        if category:
            q = q.filter(KnowledgeInsight.category == category)
        if status:
            q = q.filter(KnowledgeInsight.status == status)
        
        q = q.order_by(KnowledgeInsight.created_at.desc()).limit(limit)
        insights = q.all()
        
        return jsonify({
            "insights": [
                {
                    "id": i.id,
                    "content": i.content,
                    "category": i.category,
                    "confidence": i.confidence,
                    "tags": i.tags,
                    "status": i.status,
                    "pushed_to_knowledge": bool(i.pushed_to_knowledge),
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in insights
            ],
            "count": len(insights),
        })
    finally:
        db.close()


@knowledge_bp.post("/extract")
def extract_insights():
    """从 semantic 记忆中提取知识洞察
    
    请求体:
    {
        "user_id": "xxx",
        "project_id": "yyy",
        "save_to_db": true
    }
    """
    data = request.get_json() or {}
    user_id = data.get("user_id")
    project_id = data.get("project_id")
    save_to_db = data.get("save_to_db", True)
    
    db: Session = SessionLocal()
    try:
        # 获取 semantic 记忆
        q = db.query(Memory).filter(Memory.type == "semantic")
        if user_id:
            q = q.filter(Memory.user_id == user_id)
        if project_id:
            q = q.filter(Memory.project_id == project_id)
        
        q = q.order_by(Memory.importance.desc(), Memory.created_at.desc()).limit(50)
        memories = q.all()
        
        if not memories:
            return jsonify({"insights": [], "message": "没有找到 semantic 记忆"})
        
        semantic_items = [
            {"text": m.text, "tags": m.tags, "importance": float(m.importance or 0)}
            for m in memories
        ]
        
        # 调用 LLM 提取知识
        insights = extract_knowledge_insights(project_id, semantic_items)
        
        # 保存到数据库
        saved_count = 0
        if save_to_db and insights:
            for insight in insights:
                ki = KnowledgeInsight(
                    user_id=user_id,
                    project_id=project_id,
                    source_type="extraction",
                    content=insight.get("content", ""),
                    category=insight.get("category", "general"),
                    confidence=float(insight.get("confidence", 0.7)),
                    tags=insight.get("tags", []),
                    status="pending",
                )
                db.add(ki)
                saved_count += 1
            db.commit()
        
        return jsonify({
            "insights": insights,
            "saved_count": saved_count,
            "source_memories_count": len(memories),
        })
    finally:
        db.close()


@knowledge_bp.post("/insights/<int:insight_id>/approve")
def approve_insight(insight_id: int):
    """审核通过知识洞察"""
    db: Session = SessionLocal()
    try:
        insight = db.query(KnowledgeInsight).filter(KnowledgeInsight.id == insight_id).first()
        if not insight:
            return jsonify({"error": "Insight not found"}), 404
        
        insight.status = "approved"
        insight.updated_at = datetime.now()
        db.commit()
        
        return jsonify({"success": True, "status": "approved"})
    finally:
        db.close()


@knowledge_bp.post("/insights/<int:insight_id>/reject")
def reject_insight(insight_id: int):
    """拒绝知识洞察"""
    db: Session = SessionLocal()
    try:
        insight = db.query(KnowledgeInsight).filter(KnowledgeInsight.id == insight_id).first()
        if not insight:
            return jsonify({"error": "Insight not found"}), 404
        
        insight.status = "rejected"
        insight.updated_at = datetime.now()
        db.commit()
        
        return jsonify({"success": True, "status": "rejected"})
    finally:
        db.close()


@knowledge_bp.post("/insights/push")
def push_to_knowledge_service():
    """将已审核的知识洞察推送到知识库服务
    
    请求体:
    {
        "project_id": "yyy",
        "collection_id": 1,        // 目标知识集合 ID
        "domain": "test_experience", // 领域标识
        "insight_ids": [1, 2, 3]   // 可选，不传则推送所有 approved 的
    }
    """
    import httpx
    from ..embeddings_client import generate_embedding
    
    data = request.get_json() or {}
    project_id = data.get("project_id")
    collection_id = data.get("collection_id")
    domain = data.get("domain", "experience")
    insight_ids = data.get("insight_ids")
    
    knowledge_service_url = os.getenv("KNOWLEDGE_SERVICE_URL", "http://127.0.0.1:5001")
    
    db: Session = SessionLocal()
    try:
        q = db.query(KnowledgeInsight).filter(
            KnowledgeInsight.status == "approved",
            KnowledgeInsight.pushed_to_knowledge == False,
        )
        if project_id:
            q = q.filter(KnowledgeInsight.project_id == project_id)
        if insight_ids:
            q = q.filter(KnowledgeInsight.id.in_(insight_ids))
        
        insights = q.all()
        
        if not insights:
            return jsonify({"message": "没有待推送的知识洞察", "pushed_count": 0})
        
        pushed_count = 0
        failed_count = 0
        errors = []
        
        for insight in insights:
            try:
                # 1. 生成 embedding
                embedding = None
                try:
                    embedding = generate_embedding(insight.content)
                except Exception:
                    pass
                
                # 2. 调用 knowledge 服务创建 chunk
                chunk_data = {
                    "collection_id": collection_id,
                    "domain": domain,
                    "text": insight.content,
                    "tags": insight.tags or [],
                    "embedding": embedding,
                    "importance": insight.confidence,
                    "metadata": {
                        "source": "knowledge_insight",
                        "insight_id": insight.id,
                        "category": insight.category,
                        "project_id": insight.project_id,
                    }
                }
                
                with httpx.Client(timeout=30) as client:
                    resp = client.post(
                        f"{knowledge_service_url}/api/knowledge/chunks/ingest",
                        json=chunk_data
                    )
                    resp.raise_for_status()
                
                # 3. 更新状态
                insight.pushed_to_knowledge = True
                insight.pushed_at = datetime.now()
                insight.status = "pushed"
                pushed_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append(f"insight {insight.id}: {str(e)}")
        
        db.commit()
        
        return jsonify({
            "success": True,
            "pushed_count": pushed_count,
            "failed_count": failed_count,
            "errors": errors[:5] if errors else [],
            "message": f"已推送 {pushed_count} 条知识到知识库",
        })
    finally:
        db.close()


@knowledge_bp.get("/reflections")
def list_reflections():
    """获取自我反省记录"""
    user_id = request.args.get("user_id")
    project_id = request.args.get("project_id")
    limit = int(request.args.get("limit", 50))
    
    db: Session = SessionLocal()
    try:
        q = db.query(SelfReflection)
        
        if user_id:
            q = q.filter(SelfReflection.user_id == user_id)
        if project_id:
            q = q.filter(SelfReflection.project_id == project_id)
        
        q = q.order_by(SelfReflection.created_at.desc()).limit(limit)
        reflections = q.all()
        
        return jsonify({
            "reflections": [
                {
                    "id": r.id,
                    "satisfaction_score": r.satisfaction_score,
                    "problem_solved": bool(r.problem_solved),
                    "completeness": r.completeness,
                    "summary": r.summary,
                    "strengths": r.strengths,
                    "weaknesses": r.weaknesses,
                    "suggestions": r.suggestions,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reflections
            ],
            "count": len(reflections),
        })
    finally:
        db.close()


@knowledge_bp.get("/reflections/stats")
def reflection_stats():
    """获取反省统计数据"""
    user_id = request.args.get("user_id")
    project_id = request.args.get("project_id")
    
    db: Session = SessionLocal()
    try:
        from sqlalchemy import func
        
        q = db.query(
            func.avg(SelfReflection.satisfaction_score).label("avg_score"),
            func.count(SelfReflection.id).label("total_count"),
            func.sum(SelfReflection.problem_solved).label("solved_count"),
        )
        
        if user_id:
            q = q.filter(SelfReflection.user_id == user_id)
        if project_id:
            q = q.filter(SelfReflection.project_id == project_id)
        
        result = q.first()
        
        total = result.total_count or 0
        solved = result.solved_count or 0
        
        return jsonify({
            "avg_satisfaction_score": round(float(result.avg_score or 0), 2),
            "total_conversations": total,
            "problems_solved": solved,
            "solve_rate": round(solved / total * 100, 1) if total > 0 else 0,
        })
    finally:
        db.close()
