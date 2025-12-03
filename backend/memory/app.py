from flask import Flask
from flask_cors import CORS

from routes import memory_bp
from repository.db_session import init_db

def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    init_db()  # 应用启动时确保表存在

    # 注册 memory 蓝图，统一挂载到 /api/memory
    app.register_blueprint(memory_bp, url_prefix="/api/memory")

    @app.route("/")
    def index():
        return {"service": "memRagAgent-memory", "status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)