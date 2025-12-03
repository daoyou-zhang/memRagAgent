from flask import Blueprint

from .health import register_health_routes
from .memories import memories_bp

memory_bp = Blueprint("memory", __name__)


def register_blueprints() -> None:
    register_health_routes(memory_bp)
    memory_bp.register_blueprint(memories_bp)


# 模块导入时自动注册子路由
register_blueprints()