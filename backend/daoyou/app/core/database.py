from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# 从环境变量读取 PostgreSQL 配置
POSTGRES_USER = os.getenv("POSTGRES_USER", "daoyou_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "daoyou123456")
POSTGRES_DB = os.getenv("POSTGRES_DB", "daoyou")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# SSL配置（如果是远程连接，默认启用）
POSTGRES_SSL = os.getenv("POSTGRES_SSL", "true").lower() == "true"

# 构建数据库连接URL
# 如果明确设置了POSTGRES_SSL=true且不是本地，才使用SSL
# 否则允许自动协商（服务器不支持SSL时会降级为无SSL）
if POSTGRES_SSL and POSTGRES_HOST not in ["localhost", "127.0.0.1"]:
    # 远程连接尝试使用SSL，但不强制
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=prefer"
    )
else:
    # 本地连接或未启用SSL
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接数
    pool_pre_ping=True,  # 连接前ping测试
    pool_recycle=3600,  # 连接回收时间（秒）
    echo=False  # 是否打印SQL语句
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 统一 SQL 错误监听，打印首个失败 SQL 与参数，便于定位根因
sql_error_logger = logging.getLogger("sqlalchemy.error")

@event.listens_for(Engine, "handle_error")
def _sqla_handle_error(ctx):
    try:
        sql_error_logger.error(
            "SQL_ERROR stmt=%s params=%s orig=%s",
            ctx.statement,
            ctx.parameters,
            getattr(ctx, "original_exception", None),
        )
    except Exception:
        pass

from neo4j import GraphDatabase
import logging

logging.getLogger("neo4j").setLevel(logging.ERROR)
logging.getLogger("neo4j.bolt").setLevel(logging.ERROR)

class Neo4jDatabase:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://neo4j:7687",
            auth=("neo4j", "daoyou123456"),
            logging_level="ERROR"  # 只显示错误
        )