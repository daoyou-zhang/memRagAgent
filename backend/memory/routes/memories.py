from flask import Blueprint, jsonify, request
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import TEXT
from sqlalchemy.orm import Session

from repository.db_session import SessionLocal
from models.memory import Memory, MemoryGenerationJob
from llm_client import generate_episodic_summary

memories_bp = Blueprint("memories", __name__)

@memories_bp.post("/memories")
def create_memory():
    payload = request.get_json(force=True) or {}

    user_id = payload.get("user_id")
    agent_id = payload.get("agent_id")
    project_id = payload.get("project_id")

    m_type = payload.get("type", "semantic")
    source = payload.get("source", "system")
    text = payload.get("text")
    importance = payload.get("importance", 0.5)
    emotion = payload.get("emotion")
    tags = payload.get("tags")
    metadata = payload.get("metadata")

    if not text:
        return jsonify({"error": "field 'text' is required"}), 400

    mem = Memory(
        user_id=user_id,
        agent_id=agent_id,
        project_id=project_id,
        type=m_type,
        source=source,
        text=text,
        importance=importance,
        emotion=emotion,
        tags=tags,
        extra_metadata=metadata,
    )

    db: Session = SessionLocal()
    try:
        db.add(mem)
        db.commit()
        db.refresh(mem)
    finally:
        db.close()

    return jsonify(
        {
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
            "created_at": mem.created_at.isoformat() if mem.created_at else None,
            "last_access_at": mem.last_access_at.isoformat()
            if mem.last_access_at
            else None,
            "recall_count": mem.recall_count,
        }
    ), 201


@memories_bp.post("/jobs/episodic")
def create_episodic_job():
    payload = request.get_json(force=True) or {}

    user_id = payload.get("user_id")
    agent_id = payload.get("agent_id")
    project_id = payload.get("project_id")
    session_id = payload.get("session_id")
    start_message_id = payload.get("start_message_id")
    end_message_id = payload.get("end_message_id")

    if not session_id:
        return jsonify({"error": "field 'session_id' is required"}), 400

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

        jobs = []
        for job in q.all():
            jobs.append(
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

        return jsonify({"items": jobs})
    finally:
        db.close()


@memories_bp.post("/jobs/<int:job_id>/run")
def run_job(job_id: int):

    db: Session = SessionLocal()
    try:
        job = db.query(MemoryGenerationJob).filter(MemoryGenerationJob.id == job_id).first()
        if not job:
            return jsonify({"error": "job not found"}), 404

        if job.status not in ("pending", "failed"):
            return jsonify({"error": f"job status is {job.status}, cannot run"}), 400

        job.status = "running"
        job.error_message = None
        db.commit()
        db.refresh(job)

        try:
            summary_text = generate_episodic_summary(
                session_id=job.session_id,
                start_message_id=job.start_message_id,
                end_message_id=job.end_message_id,
            )

            mem = Memory(
                user_id=job.user_id,
                agent_id=job.agent_id,
                project_id=job.project_id,
                type="episodic",
                source="auto_session_summary",
                text=summary_text,
                importance=0.7,
                tags=["session_summary"],
                extra_metadata={
                    "job_id": job.id,
                    "session_id": job.session_id,
                    "start_message_id": job.start_message_id,
                    "end_message_id": job.end_message_id,
                },
            )

            db.add(mem)
            job.status = "done"
            job.error_message = None
            db.commit()
            db.refresh(job)
            db.refresh(mem)

            return jsonify(
                {
                    "job": {
                        "id": job.id,
                        "status": job.status,
                        "updated_at": job.updated_at.isoformat(),
                    },
                    "memory": {
                        "id": mem.id,
                        "type": mem.type,
                        "source": mem.source,
                        "text": mem.text,
                        "importance": mem.importance,
                        "tags": mem.tags,
                        "metadata": mem.extra_metadata,
                    },
                }
            )
        except Exception as e:  
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
            db.refresh(job)
            return jsonify({"error": "failed to run job", "detail": str(e)}), 500

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