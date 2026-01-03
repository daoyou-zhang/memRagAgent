#!/bin/bash
# AI Agent Person 启动脚本（Linux/Mac）

echo "╔══════════════════════════════════════════════════════════╗"
echo "║          AI Agent Person 启动中...                       ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# 切换到 backend 目录
cd "$BACKEND_DIR"

# 加载环境变量
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    echo "✅ 加载环境变量: $ENV_FILE"
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
else
    echo "⚠️  未找到 .env 文件: $ENV_FILE"
fi

# 获取端口
PORT=${AGENT_PERSON_PORT:-8001}

echo ""
echo "🚀 服务地址: http://localhost:$PORT"
echo "📚 API 文档: http://localhost:$PORT/docs"
echo "🔌 WebSocket: ws://localhost:$PORT/api/v1/chat/ws"
echo "💚 健康检查: http://localhost:$PORT/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动服务
python -m uvicorn agent_person.app:app --host 0.0.0.0 --port $PORT --reload
