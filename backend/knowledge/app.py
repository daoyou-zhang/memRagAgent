from __future__ import annotations

from flask import Flask
from flask_cors import CORS

from .routes.knowledge import knowledge_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)  # 允许跨域

    # 简单健康检查路由前缀：/api/knowledge
    app.register_blueprint(knowledge_bp, url_prefix="/api/knowledge")
    
    @app.route("/")
    def index():
        return {"service": "memRagAgent-knowledge", "status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
