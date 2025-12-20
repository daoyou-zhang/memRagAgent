from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from . import Base

class AIPrompt(Base):
    __tablename__ = "ai_prompts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    service_key = Column(String(32), nullable=False)
    level = Column(Integer, nullable=False)
    prompt_type = Column(String(32), nullable=False)  # intent, chat, analysis
    system_prompt = Column(Text, nullable=False)
    user_prompt_template = Column(Text)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('service_key', 'level', 'prompt_type', name='uq_ai_prompt'),
    ) 