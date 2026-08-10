from sqlalchemy import Column, String, Integer, Boolean, DateTime
from datetime import datetime
from app.core.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class StoreSettings(Base):
    __tablename__ = "StoreSettings"

    id = Column(String, primary_key=True, default=generate_uuid)
    shop = Column(String, unique=True, nullable=False)
    
    maxDiscountMargin = Column(Integer, default=15)
    cartAbandonmentDelay = Column(Integer, default=60)
    cartFollowupHours = Column(Integer, default=24)
    wishlistPriceDrop = Column(Boolean, default=True)
    wishlistLowStock = Column(Boolean, default=True)
    wishlistReminderDays = Column(Integer, default=3)
    minCartAmount = Column(Integer, default=30)
    quietHoursEnabled = Column(Boolean, default=False)
    quietHoursStart = Column(String, default="22:00")
    quietHoursEnd = Column(String, default="08:00")
    allowFreeShipping = Column(Boolean, default=False)
    aiPersonaTone = Column(String, default="friendly")
    
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def bot_commission_rate(self):
        from decimal import Decimal
        return Decimal("12.00")
        
    @property
    def assisted_commission_rate(self):
        from decimal import Decimal
        return Decimal("4.00")
        
    @property
    def min_fee_guard(self):
        from decimal import Decimal
        return Decimal("15.00")

# Alias for backwards compatibility with commission_engine.py
Store = StoreSettings
