from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import get_db
from app.models.store import StoreSettings
from app.models.conversation import Conversation, ConversationStatus

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

class SettingsPayload(BaseModel):
    tone: str
    maxDiscount: int
    quietHours: bool

@router.get("/analytics/summary")
async def get_analytics_summary(db: AsyncSession = Depends(get_db)):
    # Calculate metrics across all conversations
    total_recovered_result = await db.execute(
        select(func.sum(Conversation.total_recovered_amount)).where(Conversation.status == ConversationStatus.SUCCESS)
    )
    total_recovered = total_recovered_result.scalar() or 0.0

    total_commission_result = await db.execute(
        select(func.sum(Conversation.commission_earned)).where(Conversation.status == ConversationStatus.SUCCESS)
    )
    total_commission = total_commission_result.scalar() or 0.0

    active_sessions_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.status.in_([ConversationStatus.NEGOTIATION, ConversationStatus.HUMAN_ACTIVE])
        )
    )
    active_sessions = active_sessions_result.scalar() or 0

    total_sessions_result = await db.execute(select(func.count(Conversation.id)))
    total_sessions = total_sessions_result.scalar() or 0
    
    success_sessions_result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.status == ConversationStatus.SUCCESS)
    )
    success_sessions = success_sessions_result.scalar() or 0
    
    recovery_rate = (success_sessions / total_sessions * 100) if total_sessions > 0 else 0.0

    return {
        "recoveredRevenue": float(total_recovered),
        "activeSessions": active_sessions,
        "recoveryRate": round(recovery_rate, 1),
        "estimatedCommission": float(total_commission)
    }

@router.get("/conversations/active")
async def get_active_conversations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.status.in_([ConversationStatus.NEGOTIATION, ConversationStatus.HUMAN_ACTIVE, ConversationStatus.SUCCESS]))
        .order_by(Conversation.scheduled_at.desc())
        .limit(20)
    )
    conversations = result.scalars().all()

    response = []
    for conv in conversations:
        cart_value = "₺0"
        items = []
        if conv.cart_data:
            cart_value = f"₺{conv.cart_data.get('total_price', '0')}"
            for item in conv.cart_data.get("line_items", []):
                variant_title = item.get("variant_title", "")
                title = item.get("title", "")
                if variant_title and variant_title != "Default Title":
                    items.append(f"{title} ({variant_title})")
                else:
                    items.append(title)
        
        response.append({
            "id": conv.id,
            "phone": conv.customer_phone,
            "value": cart_value,
            "items": items,
            "status": conv.status.value,
            "timeElapsed": "Just now" # Simplify for now
        })
        
    return response

@router.post("/conversations/{conversation_id}/takeover")
async def trigger_takeover(conversation_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conv = result.scalar_one_or_none()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv.status = ConversationStatus.HUMAN_ACTIVE
    conv.conversion_type = "ASSISTED"
    await db.commit()
    return {"status": "ok", "message": "Takeover successful"}

@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StoreSettings).limit(1))
    store = result.scalar_one_or_none()
    
    if not store:
        store = StoreSettings(shop="default.myshopify.com")
        db.add(store)
        await db.commit()
        await db.refresh(store)
        
    return {
        "tone": store.aiPersonaTone,
        "maxDiscount": store.maxDiscountMargin,
        "quietHours": store.quietHoursEnabled
    }

@router.put("/settings")
async def update_settings(payload: SettingsPayload, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StoreSettings).limit(1))
    store = result.scalar_one_or_none()
    
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
        
    store.aiPersonaTone = payload.tone
    store.maxDiscountMargin = payload.maxDiscount
    store.quietHoursEnabled = payload.quietHours
    await db.commit()
    return {"status": "ok"}
