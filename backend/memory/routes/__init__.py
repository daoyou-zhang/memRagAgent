from flask import Blueprint

from .health import register_health_routes
from .memories import memories_bp
from .rag import rag_bp

memory_bp = Blueprint("memory", __name__)


def register_blueprints() -> None:
    register_health_routes(memory_bp)
    memory_bp.register_blueprint(memories_bp)
    # RAG 相关路由统一挂在 /api/memory/rag
    memory_bp.register_blueprint(rag_bp, url_prefix="/rag")


# 模块导入时自动注册子路由
register_blueprints()