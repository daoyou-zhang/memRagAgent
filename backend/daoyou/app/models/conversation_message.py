from sqlalchemy import Column, BigInteger, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from . import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False, index=True)
    user_id = Column(String(64))
    agent_id = Column(String(64))
    project_id = Column(String(128))
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    extra_metadata = Column("metadata", JSONB)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
