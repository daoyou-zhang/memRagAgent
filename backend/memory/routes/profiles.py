import os

from flask import Blueprint, jsonify, request
from sqlalchemy.orm import Session

from repository.db_session import SessionLocal
from models.memory import Memory, Profile
from llm_client import generate_profile_from_semantics

profiles_bp = Blueprint("profiles", __name__)


@profiles_bp.get("/<user_id>")
def get_profile(user_id: str):
    project_id = request.args.get("project_id")
    force_refresh_raw = request.args.get("force_refresh")
    force_refresh = (
        isinstance(force_refresh_raw, str)
        and force_refresh_raw.lower() in {"1", "true", "yes"}
    )

    # 画像自动刷新开关与阈值，来自 .env，全局控制成本：
    # - PROFILE_AUTO_REFRESH_ENABLED=false 时，仅在 force_refresh=true 或没有缓存时才会调用 LLM
    # - PROFILE_MIN_NEW_SEMANTIC_FOR_REFRESH 控制自动刷新的 semantic 增量阈值
    auto_refresh_enabled = (
        os.getenv("PROFILE_AUTO_REFRESH_ENABLED", "true").lower() in {"1", "true", "yes"}
    )
    min_new_semantic_for_refresh = int(
        os.getenv("PROFILE_MIN_NEW_SEMANTIC_FOR_REFRESH", "3")
    )

    db: Session = SessionLocal()
    try:
        # 如果不强制刷新，优先尝试从 profiles 表读取缓存
        aggregated_profile = None
        cached = (
            db.query(Profile)
            .filter(Profile.user_id == user_id, Profile.project_id == project_id)
            .first()
        )

        # 若存在缓存且未显式要求刷新，再根据全局配置检查“是否有足量新 semantic 记忆”
        should_refresh_due_to_new_semantic = False
        if cached and not force_refresh and auto_refresh_enabled:
            new_q = db.query(Memory).filter(
                Memory.user_id == user_id,
                Memory.type == "semantic",
                Memory.created_at > cached.updated_at,
            )
            if project_id:
                new_q = new_q.filter(Memory.project_id == project_id)
            new_count = new_q.count()
            if new_count >= min_new_semantic_for_refresh:
                should_refresh_due_to_new_semantic = True

        if cached and not force_refresh and not should_refresh_due_to_new_semantic:
            aggregated_profile = cached.profile_json
            semantic_items = []  # 未重新聚合时，不返回 raw 列表（避免额外查询）
        else:
            # 重新从 semantic 记忆聚合画像
            q = db.query(Memory).filter(Memory.user_id == user_id, Memory.type == "semantic")
            if project_id:
                q = q.filter(Memory.project_id == project_id)

            q = q.order_by(Memory.importance.desc(), Memory.created_at.desc()).limit(50)
            memories = q.all()

            semantic_items = []
            for mem in memories:
                semantic_items.append(
                    {
                        "id": mem.id,
                        "text": mem.text,
                        "tags": mem.tags,
                        "importance": float(mem.importance or 0.0),
                        "created_at": mem.created_at.isoformat() if mem.created_at else None,
                    }
                )

            aggregated_profile = generate_profile_from_semantics(
                user_id=user_id,
                project_id=project_id,
                semantic_items=semantic_items,
            )

            # 将聚合画像写入 profiles 表（upsert 按 user_id + project_id）
            if aggregated_profile:
                if cached:
                    cached.profile_json = aggregated_profile
                else:
                    cached = Profile(
                        user_id=user_id,
                        project_id=project_id,
                        profile_json=aggregated_profile,
                        extra_metadata={
                            "source": "auto_profile_aggregate",
                        },
                    )
                    db.add(cached)
                db.commit()

        return jsonify(
            {
                "user_id": user_id,
                "project_id": project_id,
                "profile": {
                    "aggregated_profile": aggregated_profile,
                    "raw_semantic_memories": semantic_items if cached is None or force_refresh else [],
                },
            }
        )
    finally:
        db.close()
