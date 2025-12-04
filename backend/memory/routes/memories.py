from flask import Blueprint, jsonify, request
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Session
from sqlalchemy import func

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
)
from embeddings_client import generate_embedding

import os

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
                    "created_at": mem.created_at.isoformat()
                    if mem.created_at
                    else None,
                }
            ),
            201,
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
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat(),
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
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat(),
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
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat(),
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
                    "created_at": job.created_at.isoformat(),
                    "updated_at": job.updated_at.isoformat(),
                }
            )

        return jsonify({"items": items})
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
                        "created_at": job.created_at.isoformat(),
                        "updated_at": job.updated_at.isoformat(),
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
                        "created_at": mem.created_at.isoformat()
                        if mem.created_at
                        else None,
                        "last_access_at": mem.last_access_at.isoformat()
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


@memories_bp.post("/jobs/<int:job_id>/run")
def run_job(job_id: int):
    """执行单个 MemoryGenerationJob。

    支持的 job_type：
    - episodic_summary  → 生成一条 episodic 记忆 + 向量
    - semantic_extract  → 生成多条 semantic 记忆 + 向量
    - profile_aggregate → 聚合 semantic 生成/更新 Profile

    返回值兼容前端 JobsPage 的预期：
    - job: { id, status, updated_at }
    - 可选 memory: 最近生成的一条 Memory（仅对 episodic/semantic 返回以便调试）。
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
                            "updated_at": job.updated_at.isoformat(),
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

                mem = Memory(
                    user_id=job.user_id,
                    agent_id=job.agent_id,
                    project_id=job.project_id,
                    type="episodic",
                    source="auto_episodic_summary",
                    text=summary_text,
                    summary=None,
                    importance=0.7,
                )
                db.add(mem)
                db.flush()

                # 为 episodic 总结生成 embedding（失败不影响主流程）
                try:
                    emb = generate_embedding(summary_text)
                    db.add(
                        MemoryEmbedding(
                            memory_id=mem.id,
                            embedding=emb,
                            model_name=os.getenv("EMBEDDINGS_NAME", ""),
                        )
                    )
                except Exception:  # noqa: BLE001
                    pass

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
                    mem = Memory(
                        user_id=job.user_id,
                        agent_id=job.agent_id,
                        project_id=job.project_id,
                        type="semantic",
                        source="auto_semantic_extract",
                        text=text,
                        summary=None,
                        importance=importance,
                        tags=tags,
                    )
                    db.add(mem)
                    db.flush()

                    # 为 semantic 记忆生成 embedding（失败不影响主流程）
                    try:
                        emb = generate_embedding(text)
                        db.add(
                            MemoryEmbedding(
                                memory_id=mem.id,
                                embedding=emb,
                                model_name=os.getenv("EMBEDDINGS_NAME", ""),
                            )
                        )
                    except Exception:  # noqa: BLE001
                        pass

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
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
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