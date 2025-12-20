#!/usr/bin/env python
"""启动所有后端服务 (跨平台)"""
import os
import sys
import time
import subprocess
import platform

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = platform.system() == "Windows"


def print_header():
    print("=" * 50)
    print("  memRagAgent 后端服务启动脚本")
    print("=" * 50)


def start_service(name: str, module: str, port: int):
    """启动服务进程

    为了支持包内相对导入，统一使用 `python -m <module>` 从 backend 根目录启动，
    如 memory.app / knowledge.app。
    """
    print(f"\n[启动] {name} 服务 (端口 {port})...")

    if IS_WINDOWS:
        # Windows: 新开 cmd 窗口，在 backend 根目录执行 python -m <module>
        cmd = f'start "{name}" cmd /k "cd /d {SCRIPT_DIR} && python -m {module}"'
        subprocess.Popen(cmd, shell=True)
    else:
        # Linux/macOS: 后台运行
        log_file = os.path.join(SCRIPT_DIR, "logs", f"{name.lower()}.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        subprocess.Popen(
            ["python", "-m", module],
            cwd=SCRIPT_DIR,
            stdout=open(log_file, "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    print(f"  ✓ {name} 已启动")


def main():
    print_header()
    
    # 启动 Memory 服务
    start_service("Memory", "memory.app", 5000)
    
    # 启动 Knowledge 服务
    start_service("Knowledge", "knowledge.app", 5001)
    
    # 等待依赖服务启动
    print("\n等待依赖服务启动 (3秒)...")
    time.sleep(3)
    
    # 打印状态
    print("\n" + "=" * 50)
    print("  服务状态")
    print("=" * 50)
    print("  - Memory:      http://localhost:5000")
    print("  - Knowledge:   http://localhost:5001")
    print("  - Agent:       http://localhost:8000 (即将启动)")
    print("=" * 50)
    
    # 启动 Agent 服务 (前台运行)
    print("\n[启动] daoyou_agent 服务 (端口 8000)...\n")
    os.chdir(SCRIPT_DIR)
    os.system("python -m uvicorn daoyou_agent.app:app --host 0.0.0.0 --port 8000 --reload")


if __name__ == "__main__":
    main()
