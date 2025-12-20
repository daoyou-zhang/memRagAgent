import os
import threading
import time
from datetime import datetime, time as dtime

import requests
from flask import Flask
from flask_cors import CORS

from .routes import memory_bp
from .routes.profiles import profiles_bp
from .routes.rag import rag_bp
from .routes.knowledge import knowledge_bp
from .routes.conversations import conversations_bp
from .routes.prompt_evolution import prompt_evolution_bp
from .routes.tenants import tenants_bp
from .repository.db_session import init_db, SessionLocal
from .models.memory import MemoryGenerationJob


JOB_SCHEDULER_ENABLED = (
    os.getenv("JOB_SCHEDULER_ENABLED", "true").lower() in {"1", "true", "yes"}
)
JOB_RUN_WINDOW_SEMANTIC = os.getenv("JOB_RUN_WINDOW_SEMANTIC", "")
JOB_RUN_WINDOW_PROFILE = os.getenv("JOB_RUN_WINDOW_PROFILE", "")


def _parse_window(window_str: str) -> tuple[dtime, dtime] | None:
    if not window_str:
        return None
    try:
        start_str, end_str = window_str.split("-")
        sh, sm = [int(x) for x in start_str.split(":", 1)]
        eh, em = [int(x) for x in end_str.split(":", 1)]
        return dtime(sh, sm), dtime(eh, em)
    except Exception:
        return None


def _in_window(now_t: dtime, start_end: tuple[dtime, dtime] | None) -> bool:
    if not start_end:
        return True
    start, end = start_end
    if start <= end:
        return start <= now_t <= end
    # 跨午夜窗口，例如 23:00-02:00
    return now_t >= start or now_t <= end


def _job_scheduler_tick(base_url: str) -> None:
    """执行一轮简单的 Job 执行调度。

    - 按 job_type 划分时间窗口：episodic / semantic / profile；
    - 仅在落在对应窗口内时，才对该类型的 pending Job 调用 /jobs/<id>/run；
    - 每轮对每种类型最多处理少量 Job，避免阻塞主线程。
    """

    now_t = datetime.now().time()

    type_windows: dict[str, tuple[dtime, dtime] | None] = {
        # 精简：主要使用 unified_memory，保留旧类型向后兼容
        "unified_memory": _parse_window(JOB_RUN_WINDOW_EPISODIC),  # 统一记忆生成
        "profile_aggregate": _parse_window(JOB_RUN_WINDOW_PROFILE),
        # 向后兼容（逐步废弃）
        "episodic_summary": _parse_window(JOB_RUN_WINDOW_EPISODIC),
        "semantic_extract": _parse_window(JOB_RUN_WINDOW_SEMANTIC),
    }

    db = SessionLocal()
    try:
        for job_type, win in type_windows.items():
            if not _in_window(now_t, win):
                continue

            q = (
                db.query(MemoryGenerationJob)
                .filter(
                    MemoryGenerationJob.job_type == job_type,
                    MemoryGenerationJob.status == "pending",
                )
                .order_by(MemoryGenerationJob.created_at.asc())
                .limit(5)
            )

            for job in q.all():
                try:
                    # 通过现有 REST 接口执行 Job，避免重复业务逻辑。
                    url = f"{base_url}/api/memory/jobs/{job.id}/run"
                    requests.post(url, timeout=15)
                except Exception:
                    # 调度失败不影响下一个 job，错误信息已在后端 run_job 中处理。
                    continue
    finally:
        db.close()


def _start_job_scheduler(app: Flask) -> None:
    if not JOB_SCHEDULER_ENABLED:
        return

    base_url = os.getenv("MEMORY_SERVICE_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

    def _loop() -> None:
        with app.app_context():
            while True:
                try:
                    _job_scheduler_tick(base_url)
                except Exception:
                    # 避免调度线程因异常退出
                    pass
                time.sleep(60)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    init_db()  # 应用启动时确保表存在

    # 注册 memory 蓝图，统一挂载到 /api/memory
    app.register_blueprint(memory_bp, url_prefix="/api/memory")

    # 注册 profiles 蓝图，挂载到 /api/profiles
    app.register_blueprint(profiles_bp, url_prefix="/api/profiles")

    # 注册 RAG 蓝图，挂载到 /api/rag（与 memory_bp 下的 /rag 不冲突，便于上游直接调用）
    app.register_blueprint(rag_bp, url_prefix="/api/rag")

    # 注册知识洞察蓝图，挂载到 /api/knowledge
    app.register_blueprint(knowledge_bp, url_prefix="/api/knowledge")

    # 注册对话记录蓝图，挂载到 /api/conversations
    app.register_blueprint(conversations_bp, url_prefix="/api/conversations")

    # 注册 Prompt 进化蓝图，挂载到 /api/prompt-evolution
    app.register_blueprint(prompt_evolution_bp, url_prefix="/api/prompt-evolution")

    # 注册租户管理蓝图，挂载到 /api（路由内部已有 /tenants 等前缀）
    app.register_blueprint(tenants_bp, url_prefix="/api")

    # 启动基于 env 控制的 Job 调度线程（只负责调用已有 /jobs/<id>/run 接口）
    _start_job_scheduler(app)

    @app.route("/")
    def index():
        return {"service": "memRagAgent-memory", "status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)