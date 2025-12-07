from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Integer, String, Text, Float, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class KnowledgeCollection(Base):
    __tablename__ = "knowledge_collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    project_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_language: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    extra_metadata: Mapped[Optional[Any]] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    collection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_uri: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    extra_metadata: Mapped[Optional[Any]] = mapped_column("metadata", JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="raw")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    section_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    tags: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    embedding: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    extra_metadata: Mapped[Optional[Any]] = mapped_column("metadata", JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
