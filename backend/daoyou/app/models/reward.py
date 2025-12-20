from datetime import datetime
from sqlalchemy import Column, String, DateTime, DECIMAL
from . import Base

class Reward(Base):
    __tablename__ = 'rewards'
    id = Column(String(36), primary_key=True)
    user_phone = Column(String(11), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow) 