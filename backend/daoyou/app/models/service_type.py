from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from . import Base

# 数据库模型
class ServiceTypeDB(Base):
    __tablename__ = "service_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    key = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    icon_name = Column(String, nullable=False)
    color = Column(String, nullable=False)
    gradient = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# Pydantic 模型
class ServiceTypeBase(BaseModel):
    key: str
    title: str
    description: str
    icon_name: str
    color: str
    gradient: str

class ServiceTypeCreate(ServiceTypeBase):
    pass

class ServiceType(ServiceTypeBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True