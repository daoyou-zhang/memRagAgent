"""修复并重启服务

解决 WebSocket 库检测问题
"""
import subprocess
import sys
import os
from pathlib import Path

print("🔧 修复 WebSocket 支持...")

# 1. 安装 uvicorn[standard]
print("\n1️⃣ 安装 uvicorn[standard]...")
subprocess.run([sys.executable, "-m", "pip", "install", "uvicorn[standard]"], check=True)

# 2. 确保 websockets 已安装
print("\n2️⃣ 确保 websockets 已安装...")
subprocess.run([sys.executable, "-m", "pip", "install", "websockets"], check=True)

# 3. 加载环境变量
print("\n3️⃣ 加载环境变量...")
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)
    print(f"✅ 已加载: {env_path}")

# 4. 启动服务
print("\n4️⃣ 启动服务...")
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

# 切换到 backend 目录
backend_dir = Path(__file__).parent.parent
os.chdir(backend_dir)

# 启动 uvicorn
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "agent_person.app:app",
    "--host", "0.0.0.0",
    "--port", str(port),
    "--reload"
])
