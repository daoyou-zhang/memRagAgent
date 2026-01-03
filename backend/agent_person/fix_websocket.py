"""
修复 WebSocket 依赖并重启服务
"""
import subprocess
import sys
import os
from pathlib import Path

def find_venv():
    """查找虚拟环境"""
    current_dir = Path.cwd()
    
    # 检查常见的虚拟环境位置
    venv_names = ['venv', '.venv', 'env', '.env']
    
    # 先检查当前目录
    for name in venv_names:
        venv_path = current_dir / name
        if venv_path.exists():
            return venv_path
    
    # 检查父目录（backend）
    parent_dir = current_dir.parent
    for name in venv_names:
        venv_path = parent_dir / name
        if venv_path.exists():
            return venv_path
    
    # 检查祖父目录（项目根目录）
    grandparent_dir = parent_dir.parent
    for name in venv_names:
        venv_path = grandparent_dir / name
        if venv_path.exists():
            return venv_path
    
    return None

def get_python_executable():
    """获取 Python 可执行文件路径"""
    # 检查是否在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print(f"✅ 已在虚拟环境中: {sys.prefix}")
        return sys.executable
    
    # 尝试查找虚拟环境
    venv_path = find_venv()
    if venv_path:
        if os.name == 'nt':  # Windows
            python_exe = venv_path / 'Scripts' / 'python.exe'
        else:  # Linux/Mac
            python_exe = venv_path / 'bin' / 'python'
        
        if python_exe.exists():
            print(f"✅ 找到虚拟环境: {venv_path}")
            return str(python_exe)
    
    # 使用当前 Python
    print(f"⚠️  未找到虚拟环境，使用当前 Python: {sys.executable}")
    return sys.executable

def main():
    print("🔧 修复 WebSocket 依赖...")
    
    # 获取 Python 可执行文件
    python_exe = get_python_executable()
    
    # 安装依赖
    print("\n📦 安装依赖...")
    result = subprocess.run(
        [python_exe, "-m", "pip", "install", "-r", "requirements.txt"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ 安装失败: {result.stderr}")
        return
    
    print("✅ 依赖安装完成")
    print(result.stdout)
    
    # 启动服务
    print("\n🚀 启动服务...")
    subprocess.run([python_exe, "start.py"])

if __name__ == "__main__":
    main()
