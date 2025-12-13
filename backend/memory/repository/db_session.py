import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.memory import Base
from dotenv import load_dotenv

load_dotenv()  # 会读取当前目录或上层目录的 .env

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "118.178.183.54")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "daoyou")
POSTGRES_USER = os.getenv("POSTGRES_USER", "daoyou_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "1013966037zhy")

DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,  # 使用前检测连接是否有效，防止"server closed the connection"
    pool_recycle=300,    # 每 5 分钟回收连接，避免长时间闲置被服务器断开
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)