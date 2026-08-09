from sqlalchemy import Column, String, Numeric, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class Store(Base):
    __tablename__ = "stores"

    id = Column(String, primary_key=True)
    domain = Column(String, unique=True, nullable=False)
    platform = Column(String, default="shopify")
    
    bot_commission_rate = Column(Numeric(4, 2), default=12.00)
    assisted_commission_rate = Column(Numeric(4, 2), default=4.00)
    min_fee_guard = Column(Numeric(6, 2), default=15.00)
    
    cart_delay_minutes = Column(Numeric(4, 0), default=60) # 1 Saat
    cart_followup_hours = Column(Numeric(4, 0), default=24) # 24 Saat
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
