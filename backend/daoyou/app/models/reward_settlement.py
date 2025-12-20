from sqlalchemy import Column, String, DateTime, DECIMAL
from datetime import datetime
from . import Base

class RewardSettlement(Base):
    __tablename__ = 'reward_settlement'

    id = Column(String(36), primary_key=True)
    reward_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    referrer_id = Column(String(36), nullable=True)
    referrer_amount = Column(DECIMAL(10, 2), default=0)
    platform_amount = Column(DECIMAL(10, 2), default=0)
    commission_rate = Column(DECIMAL(5, 2), default=0)
    status = Column(String(20), default='未结算')
    created_at = Column(DateTime, default=datetime.utcnow) 