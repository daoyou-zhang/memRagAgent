"""启动脚本

使用方式：
    python start.py
    或
    python -m agent_person.start
"""
import os
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 加载环境变量
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ 已加载环境变量: {env_path}")
else:
    print(f"⚠️  未找到 .env 文件: {env_path}")

# 启动应用
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("AGENT_PERSON_PORT", 8001))
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║          AI Agent Person 启动中...                       ║
╚══════════════════════════════════════════════════════════╝

🚀 服务地址: http://localhost:{port}
📚 API 文档: http://localhost:{port}/docs
🔌 WebSocket: ws://localhost:{port}/api/v1/chat/ws
💚 健康检查: http://localhost:{port}/health

按 Ctrl+C 停止服务
""")
    
    uvicorn.run(
        "agent_person.app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
