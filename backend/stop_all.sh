#!/bin/bash
# 停止所有后端服务

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  停止所有后端服务"
echo "========================================"

# 停止 Memory 服务
if [ -f "logs/memory.pid" ]; then
    MEMORY_PID=$(cat logs/memory.pid)
    if kill -0 "$MEMORY_PID" 2>/dev/null; then
        echo "停止 Memory 服务 (PID: $MEMORY_PID)..."
        kill "$MEMORY_PID"
    fi
    rm -f logs/memory.pid
fi

# 停止 Knowledge 服务
if [ -f "logs/knowledge.pid" ]; then
    KNOWLEDGE_PID=$(cat logs/knowledge.pid)
    if kill -0 "$KNOWLEDGE_PID" 2>/dev/null; then
        echo "停止 Knowledge 服务 (PID: $KNOWLEDGE_PID)..."
        kill "$KNOWLEDGE_PID"
    fi
    rm -f logs/knowledge.pid
fi

# 停止可能残留的进程
echo "清理残留进程..."
pkill -f "memory/app.py" 2>/dev/null
pkill -f "knowledge/app.py" 2>/dev/null
pkill -f "uvicorn daoyou_agent" 2>/dev/null

echo "所有服务已停止"
