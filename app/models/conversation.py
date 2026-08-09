from enum import Enum
from sqlalchemy import Column, String, DateTime, Numeric, Enum as SQLEnum, JSON
from app.core.database import Base

class ConversationStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    PENDING = "PENDING"
    NEGOTIATION = "NEGOTIATION"
    SUCCESS = "SUCCESS"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    store_id = Column(String, nullable=False, index=True)
    customer_phone = Column(String, nullable=False, index=True)
    cart_data = Column(JSON, nullable=False)
    status = Column(SQLEnum(ConversationStatus), default=ConversationStatus.SCHEDULED)
    
    scheduled_at = Column(DateTime, nullable=False)
    conversion_type = Column(String, nullable=True) # "BOT" veya "ASSISTED"
    applied_commission_rate = Column(Numeric(4, 2), nullable=True)
    total_recovered_amount = Column(Numeric(10, 2), default=0.00)
    commission_earned = Column(Numeric(10, 2), default=0.00)
    
    last_human_activity_at = Column(DateTime, nullable=True)
