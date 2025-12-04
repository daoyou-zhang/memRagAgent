from __future__ import annotations

import math
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
            score = _cosine(q_emb, vec)
            candidates.append(
                {
                    "memory": mem,
                    "score": float(score),
                }
            )

        # 3) 按相似度排序并截断 top_k
        candidates.sort(key=lambda x: x["score"], reverse=True)
        top_candidates = candidates[:top_k]

        used_context = []
        for item in top_candidates:
            mem: Memory = item["memory"]
            used_context.append(
                {
                    "type": "memory",
                    "id": f"mem:{mem.id}",
                    "text": mem.text,
                    "score": item["score"],
                }
            )

        return jsonify(
            {
                "answer": "",  # 目前不生成最终回答，仅返回上下文
                "used_context": used_context,
                "debug_info": {
                    "total_candidates": len(candidates),
                    "top_k": top_k,
                },
            }
        )
    finally:
        db.close()
