from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from datetime import datetime
from pathlib import Path

from .api import cognitive, tools, prompts


def create_app() -> FastAPI:
    app = FastAPI(title="DaoyouAgent (memRag-integrated)", version="0.1.0")
    
    # 启动时间
    start_time = datetime.now()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(cognitive.router, prefix="/api/v1/cognitive", tags=["cognitive"])
    app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
    app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])

    @app.get("/")
    async def root():
        return {"service": "daoyou_agent", "status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "daoyou_agent"}

    # ============================================================
    # 测试页面
    # ============================================================
    
    @app.get("/test/stream")
    async def test_stream_page():
        """流式响应测试页面"""
        static_dir = Path(__file__).parent / "static"
        return FileResponse(static_dir / "test_stream.html")

    # ============================================================
    # Status 端点（供前端监控）
    # ============================================================
    
    @app.get("/api/v1/cognitive/status")
    async def cognitive_status():
        uptime = (datetime.now() - start_time).total_seconds()
        return {
            "service": "cognitive",
            "status": "running",
            "uptime_seconds": round(uptime, 1),
            "features": {
                "intent_understanding": True,
                "tool_calling": True,
                "streaming": True,
                "learning": True,
            }
        }

    @app.get("/api/v1/memory/status")
    async def memory_status():
        import os
        memory_url = os.getenv("MEMORY_SERVICE_BASE_URL", "http://127.0.0.1:5000")
        return {
            "service": "memory",
            "status": "proxy",
            "backend_url": memory_url,
            "features": {
                "episodic": True,
                "semantic": True,
                "profile": True,
                "knowledge_extraction": True,
            }
        }

    @app.get("/api/v1/knowledge/status")
    async def knowledge_status():
        return {
            "service": "knowledge",
            "status": "pending",
            "message": "Knowledge service integration pending",
        }

    @app.get("/api/v1/mcp/status")
    async def mcp_status():
        from .services.tool_registry import get_tool_registry
        registry = get_tool_registry()
        return {
            "service": "mcp_tools",
            "status": "running",
            "preset_tools": list(registry._preset_tools.keys()),
            "db_enabled": registry._db_pool is not None,
        }

    return app


app = create_app()
