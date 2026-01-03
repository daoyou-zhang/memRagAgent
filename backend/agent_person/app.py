"""AI 智能人主应用

FastAPI + WebSocket 实时交互服务
"""
import sys
from pathlib import Path

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

try:
    from .api import chat, digital_human, voice
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from agent_person.api import chat, digital_human, voice


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Agent Person",
        description="3D 智能人实时交互系统",
        version="0.1.0"
    )
    
    start_time = datetime.now()

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
    app.include_router(digital_human.router, prefix="/api/v1/digital-human", tags=["digital-human"])
    app.include_router(voice.router, prefix="/api/v1/voice", tags=["voice"])

    @app.get("/")
    async def root():
        return {
            "service": "agent_person",
            "status": "ok",
            "version": "0.1.0"
        }

    @app.get("/health")
    async def health():
        uptime = (datetime.now() - start_time).total_seconds()
        return {
            "status": "healthy",
            "service": "agent_person",
            "uptime_seconds": round(uptime, 1),
            "features": {
                "digital_human": True,
                "voice_recognition": True,
                "voice_synthesis": True,
                "real_time_chat": True,
            }
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("AGENT_PERSON_PORT", 8001))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=True
    )
