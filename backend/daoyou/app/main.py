from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.database import engine
from .models import Base
from .core.logger import setup_logging
from .routes import router
from .models.reward import Reward
from .core.init_data import init_service_types
import os

# 初始化日志
setup_logging()

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="道友AGENT",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS配置
# 注意：当 allow_credentials=True 时，allow_origins 不能是 ["*"]，必须指定具体域名
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    # 从环境变量读取，支持逗号分隔的多个域名
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
else:
    # 默认允许的域名：生产域名和本地开发环境
    allowed_origins = [
        "https://www.zdaoyou.chat",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite 默认端口
        "http://127.0.0.1:5173",
        "http://localhost:3005",
        "http://127.0.0.1:3005",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Service is running"}

# 注册路由
app.include_router(router, prefix="/api") 

# 启动事件
@app.on_event("startup")
def startup_event():
    # 初始化服务类型数据
    init_service_types()