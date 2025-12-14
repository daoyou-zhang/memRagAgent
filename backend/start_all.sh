#!/bin/bash
# Linux/macOS 启动脚本
# 启动所有后端服务：daoyou_agent, memory, knowledge

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  memRagAgent 后端服务启动脚本 (Linux)"
echo "========================================"

# 激活虚拟环境
VENV_PATH="../venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    echo -e "\n[1/4] 激活虚拟环境..."
    source "$VENV_PATH"
else
    echo -e "\n[警告] 虚拟环境不存在: $VENV_PATH"
    echo "请先创建虚拟环境: python -m venv ../venv"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 启动 Memory 服务 (端口 5000)
echo -e "\n[2/4] 启动 Memory 服务 (端口 5000)..."
cd "$SCRIPT_DIR/memory"
nohup python app.py > "$SCRIPT_DIR/logs/memory.log" 2>&1 &
MEMORY_PID=$!
echo "Memory PID: $MEMORY_PID"

# 启动 Knowledge 服务 (端口 5001)
echo "[3/4] 启动 Knowledge 服务 (端口 5001)..."
cd "$SCRIPT_DIR/knowledge"
nohup python app.py > "$SCRIPT_DIR/logs/knowledge.log" 2>&1 &
KNOWLEDGE_PID=$!
echo "Knowledge PID: $KNOWLEDGE_PID"

# 等待依赖服务启动
echo -e "\n等待依赖服务启动 (3秒)..."
sleep 3

# 保存 PID 文件
cd "$SCRIPT_DIR"
echo "$MEMORY_PID" > logs/memory.pid
echo "$KNOWLEDGE_PID" > logs/knowledge.pid

# 启动 daoyou_agent 服务 (端口 8000) - 前台运行
echo "[4/4] 启动 daoyou_agent 服务 (端口 8000)..."
echo -e "\n========================================"
echo "  所有服务已启动！"
echo "  - Memory:      http://localhost:5000 (PID: $MEMORY_PID)"
echo "  - Knowledge:   http://localhost:5001 (PID: $KNOWLEDGE_PID)"
echo "  - Agent:       http://localhost:8000"
echo "========================================"
echo -e "\n日志文件: $SCRIPT_DIR/logs/"
echo "停止服务: ./stop_all.sh"
echo ""

python -m uvicorn daoyou_agent.app:app --host 0.0.0.0 --port 8000 --reload
