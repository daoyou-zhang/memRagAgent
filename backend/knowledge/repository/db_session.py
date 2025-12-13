from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 优先加载根目录的 .env，然后加载本地 .env（本地覆盖）
backend_root = Path(__file__).parent.parent.parent
load_dotenv(backend_root / ".env")
load_dotenv()

default_host = os.getenv("POSTGRES_HOST", "118.178.183.54")
default_port = os.getenv("POSTGRES_PORT", "5432")
default_db = os.getenv("POSTGRES_DB", "daoyou")
default_user = os.getenv("POSTGRES_USER", "daoyou_user")
default_pwd = os.getenv("POSTGRES_PASSWORD", "1013966037zhy")

# 优先使用显式配置的 DATABASE_URL；否则用 POSTGRES_* 拼接；再否则退回本地默认库。
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+psycopg2://{default_user}:{default_pwd}@{default_host}:{default_port}/{default_db}",
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,   # 连接健康检查
    pool_recycle=300,     # 5 分钟回收
    pool_size=10,         # 连接池大小
    max_overflow=20,      # 最大溢出
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)
