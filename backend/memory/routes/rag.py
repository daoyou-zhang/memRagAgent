from __future__ import annotations

import math
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from sqlalchemy.orm import Session

from repository.db_session import SessionLocal
from models.memory import Memory, MemoryEmbedding
from embeddings_client import generate_embedding

rag_bp = Blueprint("rag", __name__)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _recency_score(created_at: datetime | None, half_life_days: float = 30.0) -> float:
    """将 created_at 映射为 0~1 的新鲜度分数，越新越接近 1。

    使用简单的指数衰减：score = exp(-age_days / half_life_days)。
    若无 created_at，则返回中性值 0.5。
    """

    if created_at is None:
        return 0.5

    # 统一按 UTC 处理；若是 naive datetime，直接按当前 UTC 对比即可
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
    except Exception:  # noqa: BLE001
        return 0.5


@rag_bp.post("/query")
def rag_query():
    """基于 memory_embeddings 的简单向量 RAG 查询。

    当前仅返回召回的记忆列表（used_context），不生成最终 answer，
    便于在前端 RAG Playground 中调试检索效果。
    """

    payload = request.get_json(force=True) or {}
    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    query_text = payload.get("query") or ""
    try:
        top_k = int(payload.get("top_k", 8))
    except (TypeError, ValueError):
        top_k = 8

    if not project_id:
        return jsonify({"error": "field 'project_id' is required"}), 400
    if not query_text.strip():
        return jsonify({"error": "field 'query' is required"}), 400

    # 1) 为 query 生成 embedding
    try:
        q_emb = generate_embedding(query_text)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": "failed to generate embedding", "detail": str(e)}), 500

    db: Session = SessionLocal()
    try:
        # 2) 选取候选记忆：当前简单策略为 user_id / project_id 范围内的 semantic + episodic
        q = db.query(Memory, MemoryEmbedding).join(
            MemoryEmbedding, MemoryEmbedding.memory_id == Memory.id
        )

        q = q.filter(Memory.project_id == project_id)
        if user_id:
            q = q.filter(Memory.user_id == user_id)

        q = q.filter(Memory.type.in_(["semantic", "episodic"]))

        candidates: list[dict] = []
        for mem, emb_row in q.all():
            emb = emb_row.embedding or []
            # 可能存的是 JSON 数组，这里简单做 float 转换
            try:
                vec = [float(x) for x in emb]
            except Exception:
                continue

            # 第一阶段：向量相似度
            sim = _cosine(q_emb, vec)

            # 规则加权因子
            importance = float(mem.importance or 0.0)
            if importance < 0.0:
                importance = 0.0
            if importance > 1.0:
                importance = 1.0

            recency = _recency_score(mem.created_at)

            # type 轻微偏好：semantic 略高于 episodic
            type_boost = 1.0
            if mem.type == "semantic":
                type_boost = 1.05
            elif mem.type == "episodic":
                type_boost = 0.98

            # 最终综合得分：仍然以向量相似度为主，辅以 importance / recency / type
            final_score = (
                sim * 0.7
                + importance * 0.2
                + recency * 0.1
            ) * type_boost

            candidates.append(
                {
                    "memory": mem,
                    "similarity": float(sim),
                    "importance": float(importance),
                    "recency": float(recency),
                    "score": float(final_score),
                }
            )

        # 3) 按综合得分排序并截断 top_k
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = candidates[:top_k]

        used_context = []
        total_sim = 0.0
        total_final = 0.0
        for item in top_candidates:
            mem: Memory = item["memory"]
            total_sim += float(item.get("similarity", 0.0))
            total_final += float(item.get("score", 0.0))
            used_context.append(
                {
                    "type": "memory",
                    "id": f"mem:{mem.id}",
                    "text": mem.text,
                    "score": item["score"],  # 综合得分
                    "similarity": item.get("similarity", 0.0),
                    "importance": item.get("importance", 0.0),
                    "recency": item.get("recency", 0.0),
                    "memory_type": mem.type,
                }
            )

        avg_sim = total_sim / len(top_candidates) if top_candidates else 0.0
        avg_final = total_final / len(top_candidates) if top_candidates else 0.0

        return jsonify(
            {
                "answer": "",  # 目前不生成最终回答，仅返回上下文
                "used_context": used_context,
                "debug_info": {
                    "total_candidates": len(candidates),
                    "top_k": top_k,
                    "avg_similarity_top_k": avg_sim,
                    "avg_score_top_k": avg_final,
                },
            }
        )
    finally:
        db.close()
