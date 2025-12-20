from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func

from . import Base


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), unique=True, nullable=False, index=True)
    user_id = Column(String(64))
    agent_id = Column(String(64))
    project_id = Column(String(128))
    title = Column(String(256))
    status = Column(String(32), nullable=False, server_default="active")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    closed_at = Column(DateTime)
    auto_episodic_enabled = Column(Boolean, nullable=False, server_default="true")
    auto_semantic_enabled = Column(Boolean, nullable=False, server_default="true")
    auto_profile_enabled = Column(Boolean, nullable=False, server_default="false")
