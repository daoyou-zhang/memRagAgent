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


class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    memory_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # 目前使用 JSONB 存储向量数组，后续切换到 pgvector 时只需调整列类型和 ORM 定义
    embedding: Mapped[Any] = mapped_column(JSONB, nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    auto_episodic_enabled: Mapped[bool] = mapped_column(
        Integer, nullable=False, default=1
    )
    auto_semantic_enabled: Mapped[bool] = mapped_column(
        Integer, nullable=False, default=1
    )
    auto_profile_enabled: Mapped[bool] = mapped_column(
        Integer, nullable=False, default=0
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


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    profile_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    extra_metadata: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProfileHistory(Base):
    __tablename__ = "profiles_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    extra_metadata: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeInsight(Base):
    """知识洞察 - 从对话中提取的可复用知识"""
    __tablename__ = "knowledge_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="conversation")

    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="general")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    tags: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    extra_metadata: Mapped[Optional[Any]] = mapped_column("metadata", JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    pushed_to_knowledge: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    pushed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SelfReflection(Base):
    """自我反省记录 - 对话质量评估"""
    __tablename__ = "self_reflections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    satisfaction_score: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    problem_solved: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    completeness: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")

    strengths: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    weaknesses: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    suggestions: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    intent_category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    tool_used: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )