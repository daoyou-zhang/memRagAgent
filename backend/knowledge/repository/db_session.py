from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
