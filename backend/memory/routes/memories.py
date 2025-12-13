from flask import Blueprint, jsonify, request
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from zoneinfo import ZoneInfo
from loguru import logger

from repository.db_session import SessionLocal
from models.memory import (
    Memory,
    MemoryGenerationJob,
    ConversationSession,
    ConversationMessage,
    Profile,
    ProfileHistory,
    MemoryEmbedding,
)
from llm_client import (
    generate_episodic_summary,
    generate_semantic_memories,
    generate_profile_from_semantics,
    generate_memories_unified,
    UNIFIED_MEMORY_GENERATION,
    PROMPT_EVOLUTION_ENABLED,
)
from embeddings_client import generate_embedding
from services.vector_service import get_memory_vector_service

import os
import math

# ChromaDB 开关（渐进式迁移）
USE_CHROMADB = os.getenv("USE_CHROMADB", "true").lower() == "true"


def _sync_to_chromadb(mem: "Memory", embedding: list[float]) -> bool:
    """将记忆同步写入 ChromaDB（失败不影响主流程）"""
    if not USE_CHROMADB or not embedding:
        return False
    try:
        vec_service = get_memory_vector_service()
        return vec_service.add_memory(
            memory_id=mem.id,
            text=mem.text,
            embedding=embedding,
            project_id=mem.project_id or "",
            user_id=mem.user_id,
            memory_type=mem.type,
            importance=float(mem.importance or 0.5),
            tags=mem.tags if isinstance(mem.tags, list) else None,
        )
    except Exception as e:
        logger.warning(f"[ChromaDB] sync failed for memory {mem.id}: {e}")
        return False


def _cosine(a: list[float], b: list[float]) -> float:
    """余弦相似度（fallback 用）"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def to_beijing_iso(dt: datetime | None) -> str | None:
    """将时间统一转换为北京时间字符串，用于 API 返回。

    - 若 dt 为 None，返回 None；
    - 若 dt 无 tzinfo，视为 UTC；
    - 最终转换为 Asia/Shanghai 后 isoformat。
    """

    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("Asia/Shanghai")).isoformat()


memories_bp = Blueprint("memories", __name__)


@memories_bp.post("/memories")
def create_memory():
    payload = request.get_json(force=True) or {}

    text = (payload.get("text") or "").strip()
    if not text:
        return jsonify({"error": "field 'text' is required"}), 400

    user_id = payload.get("user_id")
    agent_id = payload.get("agent_id")
    project_id = payload.get("project_id")
    mem_type = payload.get("type") or "semantic"
    source = payload.get("source") or "manual"

    importance = payload.get("importance")
    try:
        importance_f = float(importance) if importance is not None else 0.5
    except (TypeError, ValueError):
        importance_f = 0.5

    tags = payload.get("tags")
    metadata = payload.get("metadata")

    db: Session = SessionLocal()
    try:
        mem = Memory(
            user_id=user_id,
            agent_id=agent_id,
            project_id=project_id,
            type=mem_type,
            source=source,
            text=text,
            importance=importance_f,
            tags=tags,
            extra_metadata=metadata,
        )
        db.add(mem)
        db.commit()
        db.refresh(mem)

        return (
            jsonify(
                {
                    "id": mem.id,
                    "user_id": mem.user_id,
                    "agent_id": mem.agent_id,
                    "project_id": mem.project_id,
                    "type": mem.type,
                    "source": mem.source,
                    "text": mem.text,
                    "importance": mem.importance,
                    "tags": mem.tags,
                    "created_at": to_beijing_iso(mem.created_at)
                    if mem.created_at
                    else None,
                }
            ),
            201,
        )
    finally:
        db.close()


@memories_bp.post("/context/full")
def get_full_context():
    payload = request.get_json(force=True) or {}

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    session_id = payload.get("session_id")
    query_text = payload.get("query") or ""

    if not project_id:
        return jsonify({"error": "field 'project_id' is required"}), 400
    if not session_id:
        return jsonify({"error": "field 'session_id' is required"}), 400

    try:
        default_recent = int(os.getenv("FULL_CONTEXT_RECENT_MESSAGES", "20"))
    except (TypeError, ValueError):
        default_recent = 20
    try:
        default_top_k = int(os.getenv("FULL_CONTEXT_RAG_TOP_K", "8"))
    except (TypeError, ValueError):
        default_top_k = 8

    try:
        recent_limit = int(payload.get("recent_message_limit", default_recent))
    except (TypeError, ValueError):
        recent_limit = default_recent
    try:
        rag_top_k = int(payload.get("rag_top_k", default_top_k))
    except (TypeError, ValueError):
        rag_top_k = default_top_k

    db: Session = SessionLocal()
    try:
        # 1) Profile：当前 user+project 的最新画像（如无则为 None）
        profile_json = None
        if user_id:
            prof_q = db.query(Profile).filter(Profile.user_id == user_id)
            prof_q = prof_q.filter(Profile.project_id == project_id)
            profile = prof_q.order_by(Profile.updated_at.desc()).first()
            if profile is not None:
                profile_json = profile.profile_json

        # 2) Working memory：该 session 最近 N 条消息（按时间升序返回）
        msgs_q = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.id.desc())
        )
        if recent_limit > 0:
            msgs_q = msgs_q.limit(recent_limit)
        raw_msgs = list(reversed(msgs_q.all()))

        working_messages = []
        for m in raw_msgs:
            working_messages.append(
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": to_beijing_iso(m.created_at) if m.created_at else None,
                }
            )

        # 3) RAG：基于 query_text（如有）检索 semantic/episodic 记忆
        rag_memories: list[dict] = []
        rag_debug = {
            "total_candidates": 0,
            "top_k": rag_top_k,
            "avg_similarity_top_k": 0.0,
            "avg_score_top_k": 0.0,
        }

        if query_text.strip():
            try:
                q_emb = generate_embedding(query_text)
            except Exception as e:  # noqa: BLE001
                return (
                    jsonify(
                        {
                            "error": "failed to generate embedding",
                            "detail": str(e),
                        }
                    ),
                    500,
                )

            top_candidates = []
            
            if USE_CHROMADB:
                # 使用 ChromaDB 向量检索
                try:
                    vec_service = get_memory_vector_service()
                    results = vec_service.search_memories(
                        query_embedding=q_emb,
                        project_id=project_id,
                        user_id=user_id,
                        memory_types=["semantic", "episodic"],
                        top_k=rag_top_k,
                    )
                    # 批量加载 Memory 对象（性能优化：避免 N+1 查询）
                    if results:
                        memory_ids = [r.memory_id for r in results]
                        memories_map = {
                            m.id: m for m in db.query(Memory).filter(Memory.id.in_(memory_ids)).all()
                        }
                        for r in results:
                            mem = memories_map.get(r.memory_id)
                            if mem:
                                top_candidates.append({
                                    "memory": mem,
                                    "similarity": r.similarity,
                                    "importance": r.importance,
                                    "score": r.score,
                                })
                    USE_CHROMADB_FALLBACK = False
                except Exception as e:
                    logger.warning(f"[RAG] ChromaDB search failed, fallback to JSONB: {e}")
                    USE_CHROMADB_FALLBACK = True
            else:
                USE_CHROMADB_FALLBACK = True
            
            # Fallback: 使用 JSONB 向量检索
            if not top_candidates or (not USE_CHROMADB):
                q = db.query(Memory).filter(
                    Memory.project_id == project_id,
                    Memory.embedding.isnot(None),
                )
                if user_id:
                    q = q.filter(Memory.user_id == user_id)
                q = q.filter(Memory.type.in_(["semantic", "episodic"]))

                candidates: list[dict] = []
                for mem in q.all():
                    emb = mem.embedding or []
                    try:
                        vec = [float(x) for x in emb]
                    except Exception:
                        continue

                    sim = _cosine(q_emb, vec)
                    importance = float(mem.importance or 0.0)
                    importance = max(0.0, min(1.0, importance))
                    final_score = sim * 0.8 + importance * 0.2

                    candidates.append({
                        "memory": mem,
                        "similarity": float(sim),
                        "importance": float(importance),
                        "score": float(final_score),
                    })

                candidates.sort(key=lambda x: x["score"], reverse=True)
                top_candidates = candidates[:rag_top_k]

            total_sim = 0.0
            total_final = 0.0
            for item in top_candidates:
                mem = item["memory"]
                total_sim += float(item.get("similarity", 0.0))
                total_final += float(item.get("score", 0.0))
                rag_memories.append(
                    {
                        "type": "memory",
                        "id": f"mem:{mem.id}",
                        "text": mem.text,
                        "score": item["score"],
                        "similarity": item.get("similarity", 0.0),
                        "importance": item.get("importance", 0.0),
                        "recency": None,
                        "memory_type": mem.type,
                    }
                )

            rag_debug["total_candidates"] = len(candidates)
            rag_debug["avg_similarity_top_k"] = (
                total_sim / len(top_candidates) if top_candidates else 0.0
            )
            rag_debug["avg_score_top_k"] = (
                total_final / len(top_candidates) if top_candidates else 0.0
            )

        return jsonify(
            {
                "profile": profile_json,
                "working_messages": working_messages,
                "rag_memories": rag_memories,
                "rag_debug": rag_debug,
            }
        )
    finally:
        db.close()


@memories_bp.post("/jobs/episodic")
def create_episodic_job():
    payload = request.get_json(force=True) or {}

    session_id = payload.get("session_id")
    if not session_id:
        return jsonify({"error": "field 'session_id' is required"}), 400

    user_id = payload.get("user_id")
    agent_id = payload.get("agent_id")
    project_id = payload.get("project_id")
    start_message_id = payload.get("start_message_id")
    end_message_id = payload.get("end_message_id")

    db: Session = SessionLocal()
    try:
        job = MemoryGenerationJob(
            user_id=user_id,
            agent_id=agent_id,
            project_id=project_id,
            session_id=session_id,
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            job_type="episodic_summary",
            target_types=["episodic"],
            status="pending",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        return (
            jsonify(
                {
                    "id": job.id,
                    "user_id": job.user_id,
                    "agent_id": job.agent_id,
                    "project_id": job.project_id,
                    "session_id": job.session_id,
                    "start_message_id": job.start_message_id,
                    "end_message_id": job.end_message_id,
                    "job_type": job.job_type,
                    "target_types": job.target_types,
                    "status": job.status,
                    "created_at": to_beijing_iso(job.created_at),
                    "updated_at": to_beijing_iso(job.updated_at),
                }
            ),
            201,
        )
    finally:
        db.close()


@memories_bp.post("/jobs/semantic")
def create_semantic_job():
    payload = request.get_json(force=True) or {}

    session_id = payload.get("session_id")
    if not session_id:
        return jsonify({"error": "field 'session_id' is required"}), 400

    user_id = payload.get("user_id")
    agent_id = payload.get("agent_id")
    project_id = payload.get("project_id")
    start_message_id = payload.get("start_message_id")
    end_message_id = payload.get("end_message_id")

    db: Session = SessionLocal()
    try:
        job = MemoryGenerationJob(
            user_id=user_id,
            agent_id=agent_id,
            project_id=project_id,
            session_id=session_id,
            start_message_id=start_message_id,
            end_message_id=end_message_id,
            job_type="semantic_extract",
            target_types=["semantic"],
            status="pending",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        return (
            jsonify(
                {
                    "id": job.id,
                    "user_id": job.user_id,
                    "agent_id": job.agent_id,
                    "project_id": job.project_id,
                    "session_id": job.session_id,
                    "start_message_id": job.start_message_id,
                    "end_message_id": job.end_message_id,
                    "job_type": job.job_type,
                    "target_types": job.target_types,
                    "status": job.status,
                    "created_at": to_beijing_iso(job.created_at),
                    "updated_at": to_beijing_iso(job.updated_at),
                }
            ),
            201,
        )
    finally:
        db.close()


@memories_bp.post("/jobs/profile")
def create_profile_job():
    payload = request.get_json(force=True) or {}

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")

    if not user_id:
        return jsonify({"error": "field 'user_id' is required"}), 400

    db: Session = SessionLocal()
    try:
        job = MemoryGenerationJob(
            user_id=user_id,
            agent_id=None,
            project_id=project_id,
            session_id=f"profile:{user_id}:{project_id or 'global'}",
            start_message_id=None,
            end_message_id=None,
            job_type="profile_aggregate",
            target_types=["profile"],
            status="pending",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        return (
            jsonify(
                {
                    "id": job.id,
                    "user_id": job.user_id,
                    "agent_id": job.agent_id,
                    "project_id": job.project_id,
                    "session_id": job.session_id,
                    "start_message_id": job.start_message_id,
                    "end_message_id": job.end_message_id,
                    "job_type": job.job_type,
                    "target_types": job.target_types,
                    "status": job.status,
                    "created_at": to_beijing_iso(job.created_at),
                    "updated_at": to_beijing_iso(job.updated_at),
                }
            ),
            201,
        )
    finally:
        db.close()


@memories_bp.get("/jobs")
def list_jobs():
    status = request.args.get("status")
    session_id = request.args.get("session_id")

    db: Session = SessionLocal()
    try:
        q = db.query(MemoryGenerationJob)

        if status:
            q = q.filter(MemoryGenerationJob.status == status)
        if session_id:
            q = q.filter(MemoryGenerationJob.session_id == session_id)

        q = q.order_by(MemoryGenerationJob.created_at.desc())

        items = []
        for job in q.all():
            items.append(
                {
                    "id": job.id,
                    "user_id": job.user_id,
                    "agent_id": job.agent_id,
                    "project_id": job.project_id,
                    "session_id": job.session_id,
                    "start_message_id": job.start_message_id,
                    "end_message_id": job.end_message_id,
                    "job_type": job.job_type,
                    "target_types": job.target_types,
                    "status": job.status,
                    "error_message": job.error_message,
                    "created_at": to_beijing_iso(job.created_at),
                    "updated_at": to_beijing_iso(job.updated_at),
                }
            )

        return jsonify({"items": items})
    finally:
        db.close()


@memories_bp.post("/jobs/cleanup")
def cleanup_jobs():
    """手动清理 MemoryGenerationJob 记录。

    请求体示例：

    {
      "status": ["done", "failed"],   // 可选，默认只清理 done+failed
      "before": "2024-01-01T00:00:00", // 可选，北京时间，按 updated_at 早于该时间筛选
      "user_id": "u1",                 // 可选
      "project_id": "p1"               // 可选
    }
    """

    payload = request.get_json(force=True) or {}

    status_list = payload.get("status") or ["done", "failed"]
    user_id = payload.get("user_id")
    project_id = payload.get("project_id")

    # 解析 before 时间（视为北京时间，再转换为 UTC 比较 updated_at）
    before_ts: datetime | None = None
    before_raw = payload.get("before")
    if before_raw:
        try:
            local_dt = datetime.fromisoformat(before_raw.replace("Z", ""))
            if local_dt.tzinfo is None:
                local_dt = local_dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            before_ts = local_dt.astimezone(ZoneInfo("UTC"))
        except Exception:  # noqa: BLE001
            return jsonify({"error": "invalid 'before' datetime format"}), 400

    db: Session = SessionLocal()
    try:
        q = db.query(MemoryGenerationJob)

        if status_list:
            q = q.filter(MemoryGenerationJob.status.in_(status_list))
        if user_id:
            q = q.filter(MemoryGenerationJob.user_id == user_id)
        if project_id:
            q = q.filter(MemoryGenerationJob.project_id == project_id)
        if before_ts is not None:
            q = q.filter(MemoryGenerationJob.updated_at < before_ts)

        deleted = q.delete(synchronize_session=False)
        db.commit()

        return jsonify(
            {
                "deleted_jobs": int(deleted),
                "status": status_list,
                "user_id": user_id,
                "project_id": project_id,
                "before": before_raw,
            }
        )
    finally:
        db.close()


@memories_bp.post("/jobs/profile/auto")
def create_profile_job_auto():
    """根据 semantic 增量自动决定是否创建 profile_aggregate Job。

    请求体字段：
    - user_id: 必填
    - project_id: 可选
    - min_new_semantic: 可选，单次调用覆盖默认阈值

    逻辑：
    - 读取最近一次 profiles.updated_at 作为基准时间；
    - 统计该时间之后新增的 semantic 记忆条数（按 user_id + 可选 project_id）；
    - 若新增条数 >= min_new_semantic，则创建一条 profile_aggregate Job（pending）；
    - 否则返回 status=no_need，并附带统计信息。
    """

    payload = request.get_json(force=True) or {}

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")

    if not user_id:
        return jsonify({"error": "field 'user_id' is required"}), 400

    # 默认阈值来自 env：PROFILE_AUTO_JOB_MIN_NEW_SEMANTIC
    default_min_new_semantic = int(os.getenv("PROFILE_AUTO_JOB_MIN_NEW_SEMANTIC", "5"))
    try:
        min_new_semantic = int(payload.get("min_new_semantic", default_min_new_semantic))
    except (TypeError, ValueError):
        min_new_semantic = default_min_new_semantic

    db: Session = SessionLocal()
    try:
        # 1) 找到当前最新画像（若有），作为增量统计的基准时间
        prof_q = db.query(Profile).filter(Profile.user_id == user_id)
        if project_id is not None:
            prof_q = prof_q.filter(Profile.project_id == project_id)
        latest_profile = prof_q.order_by(Profile.updated_at.desc()).first()

        last_profile_ts = latest_profile.updated_at if latest_profile is not None else None

        # 2) 统计自基准时间以来新增的 semantic 记忆条数
        mem_q = db.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.type == "semantic",
        )
        if project_id is not None:
            mem_q = mem_q.filter(Memory.project_id == project_id)
        if last_profile_ts is not None:
            mem_q = mem_q.filter(Memory.created_at > last_profile_ts)

        new_count = mem_q.count()

        # 若已有画像，且增量未达到阈值，则认为暂时无需新建 Job
        if latest_profile is not None and new_count < min_new_semantic:
            return jsonify(
                {
                    "status": "no_need",
                    "user_id": user_id,
                    "project_id": project_id,
                    "new_semantic_count": new_count,
                    "min_new_semantic": min_new_semantic,
                }
            )

        # 3) 创建 profile_aggregate Job
        session_id = payload.get("session_id") or f"profile:{user_id}:{project_id or 'global'}"

        job = MemoryGenerationJob(
            user_id=user_id,
            agent_id=None,
            project_id=project_id,
            session_id=session_id,
            start_message_id=None,
            end_message_id=None,
            job_type="profile_aggregate",
            target_types=["profile"],
            status="pending",
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        return (
            jsonify(
                {
                    "status": "created",
                    "user_id": job.user_id,
                    "project_id": job.project_id,
                    "job": {
                        "id": job.id,
                        "session_id": job.session_id,
                        "job_type": job.job_type,
                        "target_types": job.target_types,
                        "status": job.status,
                        "created_at": to_beijing_iso(job.created_at),
                        "updated_at": to_beijing_iso(job.updated_at),
                    },
                    "new_semantic_count": new_count,
                    "min_new_semantic": min_new_semantic,
                }
            ),
            201,
        )
    finally:
        db.close()


@memories_bp.post("/sessions/<session_id>/close")
def close_session(session_id: str):
    """关闭会话并按 auto_* 开关自动创建相关 Job。

    - 更新 conversation_sessions.status = 'closed' 与 closed_at；
    - 若 auto_episodic_enabled，则创建 episodic_summary Job；
    - 若 auto_semantic_enabled，则创建 semantic_extract Job；
    - 若 auto_profile_enabled，则调用 profile_aggregate Job 创建逻辑（针对 user+project）。
    """

    db: Session = SessionLocal()
    try:
        sess = (
            db.query(ConversationSession)
            .filter(ConversationSession.session_id == session_id)
            .first()
        )
        if not sess:
            return jsonify({"error": "session not found"}), 404

        # 若已经是 closed，直接返回当前状态
        if sess.status == "closed":
            return jsonify({"status": "already_closed", "session_id": session_id})

        sess.status = "closed"
        sess.closed_at = func.now()

        created_jobs: list[dict] = []

        # 统计该会话的消息条数，用于按阈值控制是否创建 episodic/semantic Job
        msg_count = (
            db.query(func.count(ConversationMessage.id))
            .filter(ConversationMessage.session_id == session_id)
            .scalar()
        ) or 0

        # 从 env 读取自动生成 episodic / semantic Job 的最小消息数阈值
        try:
            episodic_min_msgs = int(os.getenv("EPISODIC_AUTO_MIN_MESSAGES", "3"))
        except (TypeError, ValueError):
            episodic_min_msgs = 3
        try:
            semantic_min_msgs = int(os.getenv("SEMANTIC_AUTO_MIN_MESSAGES", "5"))
        except (TypeError, ValueError):
            semantic_min_msgs = 5

        def _add_job(job_type: str, target_types: list[str]) -> MemoryGenerationJob:
            job = MemoryGenerationJob(
                user_id=sess.user_id,
                agent_id=sess.agent_id,
                project_id=sess.project_id,
                session_id=session_id,
                start_message_id=None,
                end_message_id=None,
                job_type=job_type,
                target_types=target_types,
                status="pending",
            )
            db.add(job)
            db.flush()
            created_jobs.append(
                {
                    "id": job.id,
                    "job_type": job.job_type,
                    "session_id": job.session_id,
                    "user_id": job.user_id,
                    "project_id": job.project_id,
                    "status": job.status,
                }
            )
            return job

        # 根据开关 + 消息条数阈值自动创建 Job
        if bool(sess.auto_episodic_enabled) and msg_count >= episodic_min_msgs:
            _add_job("episodic_summary", ["episodic"])

        if bool(sess.auto_semantic_enabled) and msg_count >= semantic_min_msgs:
            _add_job("semantic_extract", ["semantic"])

        if bool(sess.auto_profile_enabled):
            # 画像 Job 不依赖具体消息范围，只依赖 user+project
            job = MemoryGenerationJob(
                user_id=sess.user_id,
                agent_id=None,
                project_id=sess.project_id,
                session_id=f"profile:{sess.user_id}:{sess.project_id or 'global'}",
                start_message_id=None,
                end_message_id=None,
                job_type="profile_aggregate",
                target_types=["profile"],
                status="pending",
            )
            db.add(job)
            db.flush()
            created_jobs.append(
                {
                    "id": job.id,
                    "job_type": job.job_type,
                    "session_id": job.session_id,
                    "user_id": job.user_id,
                    "project_id": job.project_id,
                    "status": job.status,
                }
            )

        db.commit()

        return (
            jsonify(
                {
                    "status": "closed",
                    "session_id": session_id,
                    "auto_episodic_enabled": bool(sess.auto_episodic_enabled),
                    "auto_semantic_enabled": bool(sess.auto_semantic_enabled),
                    "auto_profile_enabled": bool(sess.auto_profile_enabled),
                    "message_count": msg_count,
                    "episodic_min_messages": episodic_min_msgs,
                    "semantic_min_messages": semantic_min_msgs,
                    "created_jobs": created_jobs,
                }
            ),
            200,
        )
    finally:
        db.close()


@memories_bp.post("/memories/query")
def query_memories():
    payload = request.get_json(force=True) or {}

    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    query_text = payload.get("query")
    top_k = int(payload.get("top_k", 10))

    # 分页参数：page 从 1 开始，page_size 控制每页数量
    try:
        page = int(payload.get("page", 1))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(payload.get("page_size", top_k)) if top_k else int(
            payload.get("page_size", 10)
        )
    except (TypeError, ValueError):
        page_size = 10

    if page < 1:
        page = 1
    if page_size <= 0:
        page_size = 10
    # 避免一次查太多
    if page_size > 100:
        page_size = 100

    filters = payload.get("filters") or {}
    types = filters.get("types")
    min_importance = filters.get("min_importance")
    tags = filters.get("tags") or []

    db: Session = SessionLocal()
    try:
        q = db.query(Memory)

        if user_id:
            q = q.filter(Memory.user_id == user_id)
        if project_id:
            q = q.filter(Memory.project_id == project_id)

        if types:
            q = q.filter(Memory.type.in_(types))
        if min_importance is not None:
            try:
                min_imp = float(min_importance)
                q = q.filter(Memory.importance >= min_imp)
            except (TypeError, ValueError):
                pass

        # very simple tag filtering: cast JSON/tags to string and ILIKE
        if tags:
            for t in tags:
                if not t:
                    continue
                q = q.filter(cast(Memory.tags, TEXT).ilike(f"%{t}%"))

        if query_text:
            q = q.filter(Memory.text.ilike(f"%{query_text}%"))

        # 先计算总数，再分页
        total = q.count()

        q = q.order_by(Memory.importance.desc(), Memory.created_at.desc())

        # 如果调用方仍然传了 top_k，则优先使用 top_k 作为上限
        effective_page_size = min(page_size, top_k) if top_k else page_size
        offset = (page - 1) * effective_page_size
        q = q.offset(offset).limit(effective_page_size)

        items = []
        for mem in q.all():
            items.append(
                {
                    "memory": {
                        "id": mem.id,
                        "user_id": mem.user_id,
                        "agent_id": mem.agent_id,
                        "project_id": mem.project_id,
                        "type": mem.type,
                        "source": mem.source,
                        "text": mem.text,
                        "summary": mem.summary,
                        "importance": mem.importance,
                        "emotion": mem.emotion,
                        "tags": mem.tags,
                        "metadata": mem.extra_metadata,
                        "created_at": to_beijing_iso(mem.created_at)
                        if mem.created_at
                        else None,
                        "last_access_at": to_beijing_iso(mem.last_access_at)
                        if mem.last_access_at
                        else None,
                        "recall_count": mem.recall_count,
                    },
                    "score": float(mem.importance or 1.0),
                }
            )

        has_next = offset + effective_page_size < total
        has_prev = page > 1

        return jsonify(
            {
                "items": items,
                "page": page,
                "page_size": effective_page_size,
                "total": total,
                "has_next": has_next,
                "has_prev": has_prev,
            }
        )
    finally:
        db.close()


@memories_bp.post("/memories/cleanup")
def cleanup_memories():
    """手动清理记忆与画像。

    支持三种 mode（针对单个 user+project）：

    - by_user: 删除该用户的指定类型记忆（可选是否删除画像）；
    - by_time: 删除 before 之前的指定类型记忆；
    - by_limit: 仅保留最近 max_keep 条指定类型记忆，其余删除；

    请求体示例：

    {
      "mode": "by_user" | "by_time" | "by_limit",
      "user_id": "u1",              // by_user / by_limit 必填
      "project_id": "p1",           // 可选
      "types": ["episodic", "semantic"], // 可选，默认两种都清
      "before": "2024-01-01T00:00:00",    // 仅 by_time 使用
      "max_keep": 1000,              // 仅 by_limit 使用
      "delete_profile": false        // 仅 by_user/by_time，可选
    }
    """

    payload = request.get_json(force=True) or {}

    mode = (payload.get("mode") or "").strip() or "by_user"
    user_id = payload.get("user_id")
    project_id = payload.get("project_id")
    types = payload.get("types") or ["episodic", "semantic"]
    delete_profile = bool(payload.get("delete_profile", False))

    if mode not in {"by_user", "by_time", "by_limit"}:
        return jsonify({"error": "invalid mode"}), 400

    if mode in {"by_user", "by_limit"} and not user_id:
        return jsonify({"error": "field 'user_id' is required for this mode"}), 400

    # 解析 before 时间（视为北京时间，再转换为 UTC 与数据库比较）
    before_ts: datetime | None = None
    if mode == "by_time":
        before_raw = payload.get("before")
        if not before_raw:
            return jsonify({"error": "field 'before' is required for mode=by_time"}), 400
        try:
            # 用户在页面填写的时间按 Asia/Shanghai 解析
            local_dt = datetime.fromisoformat(before_raw.replace("Z", ""))
            if local_dt.tzinfo is None:
                local_dt = local_dt.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            # 转换为 UTC，与数据库中的时间比较
            before_ts = local_dt.astimezone(ZoneInfo("UTC"))
        except Exception:  # noqa: BLE001
            return jsonify({"error": "invalid 'before' datetime format"}), 400

    max_keep: int | None = None
    if mode == "by_limit":
        try:
            max_keep = int(payload.get("max_keep", 1000))
        except (TypeError, ValueError):
            max_keep = 1000
        if max_keep is not None and max_keep <= 0:
            return jsonify({"error": "max_keep must be > 0"}), 400

    # 规范化 types
    valid_types = {"episodic", "semantic"}
    target_types = [t for t in types if t in valid_types]
    if not target_types:
        target_types = ["episodic", "semantic"]

    db: Session = SessionLocal()
    try:
        deleted_memories = 0
        deleted_embeddings = 0
        deleted_profiles = 0

        base_q = db.query(Memory).filter(Memory.type.in_(target_types))
        if user_id:
            base_q = base_q.filter(Memory.user_id == user_id)
        if project_id:
            base_q = base_q.filter(Memory.project_id == project_id)

        if mode == "by_user":
            mem_ids = [m.id for m in base_q.all()]
        elif mode == "by_time":
            if before_ts is not None:
                base_q = base_q.filter(Memory.created_at < before_ts)
            mem_ids = [m.id for m in base_q.all()]
        else:  # by_limit
            # 仅对单个用户生效
            q = base_q.order_by(Memory.created_at.desc())
            all_ids = [m.id for m in q.all()]
            if len(all_ids) <= (max_keep or 0):
                mem_ids = []
            else:
                mem_ids = all_ids[(max_keep or 0) :]

        if mem_ids:
            # 删除 embeddings
            deleted_embeddings = (
                db.query(MemoryEmbedding)
                .filter(MemoryEmbedding.memory_id.in_(mem_ids))
                .delete(synchronize_session=False)
            )

            # 删除 memories
            deleted_memories = (
                base_q.filter(Memory.id.in_(mem_ids))
                .delete(synchronize_session=False)
            )

        # 可选：删除画像（当前 user+project 的 Profile + ProfileHistory）
        if delete_profile and user_id:
            prof_q = db.query(Profile).filter(Profile.user_id == user_id)
            if project_id is not None:
                prof_q = prof_q.filter(Profile.project_id == project_id)
            profiles = prof_q.all()
            if profiles:
                prof_ids = [p.id for p in profiles]
                # 删除历史画像
                db.query(ProfileHistory).filter(ProfileHistory.user_id == user_id).delete(
                    synchronize_session=False
                )
                # 删除当前画像
                deleted_profiles = (
                    prof_q.filter(Profile.id.in_(prof_ids))
                    .delete(synchronize_session=False)
                )

        db.commit()

        return jsonify(
            {
                "mode": mode,
                "user_id": user_id,
                "project_id": project_id,
                "types": target_types,
                "deleted_memories": int(deleted_memories),
                "deleted_embeddings": int(deleted_embeddings),
                "deleted_profiles": int(deleted_profiles),
            }
        )
    finally:
        db.close()


@memories_bp.post("/jobs/<int:job_id>/run")
def run_job(job_id: int):
    """执行单个 MemoryGenerationJob。

    主要 job_type（推荐）：
    - unified_memory    → 一次 LLM 调用生成 episodic + semantic（默认）
    - profile_aggregate → 聚合 semantic 生成/更新 Profile
    
    兼容旧类型（逐步废弃）：
    - episodic_summary  → 仅生成 episodic
    - semantic_extract  → 仅生成 semantic

    返回值：
    - job: { id, status, updated_at }
    - 可选 memory: 最近生成的一条 Memory
    """

    db: Session = SessionLocal()
    try:
        job = db.query(MemoryGenerationJob).filter(MemoryGenerationJob.id == job_id).first()
        if not job:
            return jsonify({"error": "job not found"}), 404

        # 简单处理幂等：已完成或失败的 Job 不再重复执行
        if job.status in {"done", "failed"}:
            return (
                jsonify(
                    {
                        "job": {
                            "id": job.id,
                            "status": job.status,
                            "updated_at": to_beijing_iso(job.updated_at),
                        }
                    }
                ),
                200,
            )

        job.status = "running"
        db.flush()

        created_memory: Memory | None = None

        try:
            if job.job_type == "episodic_summary":
                # 1) 汇总该会话消息文本（简单版：按时间排序拼接）
                msgs_q = (
                    db.query(ConversationMessage)
                    .filter(ConversationMessage.session_id == job.session_id)
                    .order_by(ConversationMessage.id.asc())
                )
                texts: list[str] = []
                for m in msgs_q.all():
                    texts.append(f"[{m.role}] {m.content}")
                conversation_text = "\n".join(texts)

                summary_text = generate_episodic_summary(job.session_id, conversation_text)

                # 生成 embedding（失败不影响主流程）
                emb = None
                try:
                    emb = generate_embedding(summary_text)
                except Exception:
                    pass

                mem = Memory(
                    user_id=job.user_id,
                    agent_id=job.agent_id,
                    project_id=job.project_id,
                    type="episodic",
                    source="auto_episodic_summary",
                    text=summary_text,
                    importance=0.7,
                    embedding=emb,  # 直接存到 Memory
                    embedding_model=os.getenv("EMBEDDINGS_NAME", "") if emb else None,
                )
                db.add(mem)
                db.flush()
                
                # 同步到 ChromaDB
                if emb:
                    _sync_to_chromadb(mem, emb)

                created_memory = mem

            elif job.job_type == "semantic_extract":
                # 1) 汇总会话内容
                msgs_q = (
                    db.query(ConversationMessage)
                    .filter(ConversationMessage.session_id == job.session_id)
                    .order_by(ConversationMessage.id.asc())
                )
                texts: list[str] = []
                for m in msgs_q.all():
                    texts.append(f"[{m.role}] {m.content}")
                conversation_text = "\n".join(texts)

                items = generate_semantic_memories(job.session_id, conversation_text)

                last_mem: Memory | None = None
                for item in items:
                    text = str(item.get("text") or "").strip()
                    if not text:
                        continue
                    importance = float(item.get("importance") or 0.7)
                    tags = item.get("tags")
                    
                    # 生成 embedding
                    emb = None
                    try:
                        emb = generate_embedding(text)
                    except Exception:
                        pass
                    
                    mem = Memory(
                        user_id=job.user_id,
                        agent_id=job.agent_id,
                        project_id=job.project_id,
                        type="semantic",
                        source="auto_semantic_extract",
                        text=text,
                        importance=importance,
                        tags=tags,
                        embedding=emb,
                        embedding_model=os.getenv("EMBEDDINGS_NAME", "") if emb else None,
                    )
                    db.add(mem)
                    db.flush()
                    
                    # 同步到 ChromaDB
                    if emb:
                        _sync_to_chromadb(mem, emb)
                    
                    last_mem = mem

                created_memory = last_mem

            elif job.job_type == "profile_aggregate":
                # 基于当前 user+project 的 semantic 记忆聚合画像
                if not job.user_id:
                    raise RuntimeError("profile_aggregate job requires user_id")

                q = (
                    db.query(Memory)
                    .filter(Memory.user_id == job.user_id, Memory.type == "semantic")
                    .order_by(Memory.importance.desc(), Memory.created_at.desc())
                )
                if job.project_id:
                    q = q.filter(Memory.project_id == job.project_id)

                semantics: list[dict] = []
                for mem in q.limit(200).all():
                    semantics.append(
                        {
                            "text": mem.text,
                            "tags": mem.tags,
                            "importance": mem.importance,
                        }
                    )

                profile_json = generate_profile_from_semantics(
                    job.user_id,
                    job.project_id,
                    semantics,
                )

                # 先查是否已有当前画像
                prof_q = db.query(Profile).filter(Profile.user_id == job.user_id)
                if job.project_id is not None:
                    prof_q = prof_q.filter(Profile.project_id == job.project_id)
                profile = prof_q.first()

                if profile is not None:
                    # 将旧画像写入历史表
                    hist = ProfileHistory(
                        user_id=profile.user_id,
                        project_id=profile.project_id,
                        version=1,
                        profile_json=profile.profile_json,
                        extra_metadata=None,
                    )
                    db.add(hist)

                    profile.profile_json = profile_json
                else:
                    profile = Profile(
                        user_id=job.user_id,
                        project_id=job.project_id,
                        profile_json=profile_json,
                    )
                    db.add(profile)

            elif job.job_type == "unified_memory":
                # 统一记忆生成：一次 LLM 调用同时生成 episodic + semantic
                # 优化：原来需要 2 次 LLM 调用，现在合并为 1 次
                msgs_q = (
                    db.query(ConversationMessage)
                    .filter(ConversationMessage.session_id == job.session_id)
                    .order_by(ConversationMessage.id.asc())
                )
                texts: list[str] = []
                for m in msgs_q.all():
                    texts.append(f"[{m.role}] {m.content}")
                conversation_text = "\n".join(texts)
                
                # 一次 LLM 调用
                result = generate_memories_unified(
                    session_id=job.session_id,
                    conversation_text=conversation_text,
                    user_id=job.user_id,
                    project_id=job.project_id,
                    include_prompt_suggestions=True,
                )
                
                # 1) 存储 episodic
                episodic_text = result.get("episodic", "").strip()
                if episodic_text:
                    emb = None
                    try:
                        emb = generate_embedding(episodic_text)
                    except Exception:
                        pass
                    mem = Memory(
                        user_id=job.user_id,
                        agent_id=job.agent_id,
                        project_id=job.project_id,
                        type="episodic",
                        source="auto_unified",
                        text=episodic_text,
                        importance=0.7,
                        embedding=emb,
                        embedding_model=os.getenv("EMBEDDINGS_NAME", "") if emb else None,
                    )
                    db.add(mem)
                    db.flush()
                    if emb:
                        _sync_to_chromadb(mem, emb)
                    created_memory = mem
                
                # 2) 存储 semantic
                for item in result.get("semantic", []):
                    text = str(item.get("text") or "").strip()
                    if not text:
                        continue
                    importance = float(item.get("importance") or 0.7)
                    tags = item.get("tags")
                    emb = None
                    try:
                        emb = generate_embedding(text)
                    except Exception:
                        pass
                    mem = Memory(
                        user_id=job.user_id,
                        agent_id=job.agent_id,
                        project_id=job.project_id,
                        type="semantic",
                        source="auto_unified",
                        text=text,
                        importance=importance,
                        tags=tags,
                        embedding=emb,
                        embedding_model=os.getenv("EMBEDDINGS_NAME", "") if emb else None,
                    )
                    db.add(mem)
                    db.flush()
                    if emb:
                        _sync_to_chromadb(mem, emb)
                
                # 3) 处理 prompt 建议（如果启用）
                prompt_suggestions = result.get("prompt_suggestions", [])
                if prompt_suggestions and PROMPT_EVOLUTION_ENABLED:
                    from services.prompt_evolution import get_prompt_evolution_service
                    svc = get_prompt_evolution_service()
                    svc.process_llm_suggestions(
                        suggestions=prompt_suggestions,
                        user_id=job.user_id,
                        project_id=job.project_id,
                        trigger_type="unified_memory",
                        trigger_job_id=job.id,
                    )
                
                # 4) 判断是否需要更新画像（基于 semantic 增量，而非 LLM 判断）
                if job.user_id:
                    # 统计该用户当前 semantic 记忆总数
                    semantic_count = db.query(Memory).filter(
                        Memory.user_id == job.user_id,
                        Memory.type == "semantic",
                    ).count()
                    
                    # 获取阈值（默认 5 条 semantic 后触发画像更新）
                    try:
                        threshold = int(os.getenv("PROFILE_AUTO_JOB_MIN_NEW_SEMANTIC", "5"))
                    except (TypeError, ValueError):
                        threshold = 5
                    
                    # 检查是否已有 pending 的 profile Job，避免重复
                    existing = db.query(MemoryGenerationJob).filter(
                        MemoryGenerationJob.user_id == job.user_id,
                        MemoryGenerationJob.job_type == "profile_aggregate",
                        MemoryGenerationJob.status == "pending",
                    ).first()
                    
                    # 满足条件且无重复 Job 时创建
                    if semantic_count >= threshold and not existing:
                        profile_job = MemoryGenerationJob(
                            user_id=job.user_id,
                            project_id=job.project_id,
                            session_id=f"profile:{job.user_id}:{job.project_id or 'global'}",
                            job_type="profile_aggregate",
                            status="pending",
                        )
                        db.add(profile_job)

            else:
                raise RuntimeError(f"unsupported job_type: {job.job_type}")

            job.status = "done"
            db.commit()

        except Exception as e:  # noqa: BLE001
            job.status = "failed"
            job.error_message = str(e)
            db.commit()

        # 重新拉取一次确保 updated_at 等字段最新
        db.refresh(job)

        payload: dict[str, object] = {
            "job": {
                "id": job.id,
                "status": job.status,
                "updated_at": to_beijing_iso(job.updated_at),
            }
        }

        if created_memory is not None:
            mem = created_memory
            payload["memory"] = {
                "id": mem.id,
                "type": mem.type,
                "source": mem.source,
                "text": mem.text,
                "importance": mem.importance,
                "tags": mem.tags,
                "metadata": mem.extra_metadata,
            }

        return jsonify(payload)
    finally:
        db.close()