from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Integer,
    String,
    Text,
    Float,
    DateTime,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB  # 若当前用 SQLite 可先不用这个


class Base(DeclarativeBase):
    pass


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    emotion: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # 如果当前不是 Postgres，可以把 JSONB 换成 Text 手动存 JSON 字符串
    tags: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    extra_metadata: Mapped[Optional[Any]] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_access_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    recall_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MemoryGenerationJob(Base):
    __tablename__ = "memory_generation_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    session_id: Mapped[str] = mapped_column(String(128), nullable=False)

    start_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_types: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_id: Mapped[str] = mapped_column(String(128), nullable=False)

    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra_metadata: Mapped[Optional[Any]] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )