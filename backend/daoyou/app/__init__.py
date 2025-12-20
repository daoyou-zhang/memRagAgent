
# 应用初始化文件
from fastapi import FastAPI

app = FastAPI()

def create_app():
    """应用工厂函数"""
    from .core import events  # 导入事件处理器
    return app
