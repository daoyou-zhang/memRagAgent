from __future__ import annotations

import os
import sys
import math
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request, g
from loguru import logger
from sqlalchemy.orm import Session

# 添加 shared 模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.auth import flask_auth_required, Scopes
from ..repository.db_session import SessionLocal
from ..models.memory import Memory
from ..embeddings_client import generate_embedding
from ..services.vector_service import get_memory_vector_service

# ChromaDB 开关
USE_CHROMADB = os.getenv("USE_CHROMADB", "true").lower() == "true"

rag_bp = Blueprint("rag", __name__)


def _get_cache_service():
    """获取缓存服务（失败返回 None）"""
    try:
        from shared.cache import get_cache_service
        return get_cache_service()
    except Exception:
        return None


def _query_hash(query: str, project_id: str, user_id: str = None) -> str:
    """生成查询哈希用于缓存"""
    key = f"{query}:{project_id}:{user_id or ''}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def _recency_score(created_at: datetime | None, half_life_days: float = 30.0) -> float:
    """将 created_at 映射为 0~1 的新鲜度分数，越新越接近 1。"""
    if created_at is None:
        return 0.5

    if created_at.tzinfo is None:
        created_ts = created_at
    else:
        created_ts = created_at.astimezone(timezone.utc).replace(tzinfo=None)

    now = datetime.utcnow()
    age_days = (now - created_ts).total_seconds() / 86400.0
    if age_days <= 0:
        return 1.0

    try:
        return float(math.exp(-age_days / float(half_life_days)))
    except Exception:
        return 0.5


@rag_bp.post("/query")
@flask_auth_required(scopes=[Scopes.READ_MEMORIES])
def rag_query():
    """RAG 查询接口（优先使用 ChromaDB + Redis 缓存）"""
    payload = request.get_json(force=True) or {}
    user_id = payload.get("user_id")
    query_text = payload.get("query") or ""
    try:
        top_k = int(payload.get("top_k", 8))
    except (TypeError, ValueError):
        top_k = 8

    # 租户隔离：非管理员使用上下文中的 project_id
    auth = getattr(g, "auth", None)
    is_admin = auth and getattr(auth, "is_admin", False)
    ctx = getattr(g, "tenant_ctx", {}) or {}
    
    if is_admin:
        project_id = payload.get("project_id") or ctx.get("project_id")
    else:
        project_id = ctx.get("project_id") or payload.get("project_id")

    if not project_id:
        return jsonify({"error": "field 'project_id' is required"}), 400
    if not query_text.strip():
        return jsonify({"error": "field 'query' is required"}), 400

    # 尝试从 Redis 缓存获取
    cache = _get_cache_service()
    cache_key = _query_hash(query_text, project_id, user_id)
    if cache:
        cached_result = cache.get_rag(cache_key, project_id, user_id)
        if cached_result:
            logger.debug(f"[RAG] Cache hit for query: {query_text[:30]}...")
            return jsonify({
                "answer": "",
                "used_context": cached_result,
                "debug_info": {"from_cache": True},
            })

    # 生成 query embedding
    try:
        q_emb = generate_embedding(query_text)
    except Exception as e:
        logger.error(f"[RAG] Embedding generation failed: {e}")
        return jsonify({"error": "failed to generate embedding", "detail": str(e)}), 500

    db: Session = SessionLocal()
    try:
        top_candidates = []
        total_candidates = 0

        if USE_CHROMADB:
            # 使用 ChromaDB 向量检索
            try:
                vec_service = get_memory_vector_service()
                results = vec_service.search_memories(
                    query_embedding=q_emb,
                    project_id=project_id,
                    user_id=user_id,
                    memory_types=["semantic", "episodic"],
                    top_k=top_k,
                )
                # 批量加载 Memory 对象
                if results:
                    memory_ids = [r.memory_id for r in results]
                    memories_map = {
                        m.id: m for m in db.query(Memory).filter(Memory.id.in_(memory_ids)).all()
                    }
                    for r in results:
                        mem = memories_map.get(r.memory_id)
                        if mem:
                            recency = _recency_score(mem.created_at)
                            top_candidates.append({
                                "memory": mem,
                                "similarity": r.similarity,
                                "importance": r.importance,
                                "recency": recency,
                                "score": r.score,
                            })
                    total_candidates = len(results)
                logger.debug(f"[RAG] ChromaDB returned {len(top_candidates)} results")
            except Exception as e:
                logger.warning(f"[RAG] ChromaDB failed, fallback to JSONB: {e}")
                top_candidates = []

        # Fallback: JSONB 向量检索
        if not top_candidates:
            from ..models.memory import MemoryEmbedding
            
            def _cosine(a, b):
                if not a or not b or len(a) != len(b):
                    return 0.0
                dot = sum(x * y for x, y in zip(a, b))
                na = math.sqrt(sum(x * x for x in a))
                nb = math.sqrt(sum(y * y for y in b))
                return dot / (na * nb) if na and nb else 0.0

            q = db.query(Memory, MemoryEmbedding).join(
                MemoryEmbedding, MemoryEmbedding.memory_id == Memory.id
            )
            q = q.filter(Memory.project_id == project_id)
            if user_id:
                q = q.filter(Memory.user_id == user_id)
            q = q.filter(Memory.type.in_(["semantic", "episodic"]))

            candidates = []
            for mem, emb_row in q.all():
                try:
                    vec = [float(x) for x in (emb_row.embedding or [])]
                except Exception:
                    continue
                sim = _cosine(q_emb, vec)
                importance = max(0.0, min(1.0, float(mem.importance or 0.5)))
                recency = _recency_score(mem.created_at)
                score = sim * 0.7 + importance * 0.2 + recency * 0.1
                candidates.append({
                    "memory": mem,
                    "similarity": sim,
                    "importance": importance,
                    "recency": recency,
                    "score": score,
                })

            candidates.sort(key=lambda x: x["score"], reverse=True)
            top_candidates = candidates[:top_k]
            total_candidates = len(candidates)
            logger.debug(f"[RAG] JSONB fallback returned {len(top_candidates)} results")

        # 构建响应
        used_context = []
        total_sim = 0.0
        total_score = 0.0
        for item in top_candidates:
            mem = item["memory"]
            total_sim += item["similarity"]
            total_score += item["score"]
            used_context.append({
                "type": "memory",
                "id": f"mem:{mem.id}",
                "text": mem.text,
                "score": item["score"],
                "similarity": item["similarity"],
                "importance": item["importance"],
                "recency": item["recency"],
                "memory_type": mem.type,
            })

        # 写入缓存
        if cache and used_context:
            cache.set_rag(cache_key, project_id, used_context, user_id)

        return jsonify({
            "answer": "",
            "used_context": used_context,
            "debug_info": {
                "total_candidates": total_candidates,
                "top_k": top_k,
                "avg_similarity_top_k": total_sim / len(top_candidates) if top_candidates else 0,
                "avg_score_top_k": total_score / len(top_candidates) if top_candidates else 0,
                "from_cache": False,
            },
        })
    finally:
        db.close()
