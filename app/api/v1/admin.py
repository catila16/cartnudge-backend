import os
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.store import StoreSettings
from app.core.security import create_admin_token, verify_admin_token

router = APIRouter(prefix="/api/v1/admin", tags=["Super Admin"])

class AdminLoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def admin_login(data: AdminLoginRequest):
    env_user = os.getenv("ADMIN_USERNAME", "admin")
    env_pass = os.getenv("ADMIN_PASSWORD", "cartnudge2026!")
    
    if data.username != env_user or data.password != env_pass:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Hatalı kullanıcı adı veya şifre"
        )
    
    token = create_admin_token(username=data.username)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/metrics")
async def get_admin_metrics(
    db: AsyncSession = Depends(get_db),
    admin_user: str = Depends(verify_admin_token)
):
    # 1. Aktif Mağazalar (uninstalled_at boş olanlar)
    stmt = select(StoreSettings).where(
        StoreSettings.uninstalled_at.is_(None),
        StoreSettings.is_active == True
    )
    result = await db.execute(stmt)
    active_stores = result.scalars().all()
    
    active_stores_count = len(active_stores)

    # 2. Ülke Bazlı Dağılım (Aggregation)
    c_stmt = select(
        StoreSettings.country_code,
        func.count(StoreSettings.id).label("total")
    ).where(
        StoreSettings.uninstalled_at.is_(None)
    ).group_by(StoreSettings.country_code)
    
    c_result = await db.execute(c_stmt)
    country_counts = c_result.all()

    country_breakdown = [
        {"country": c[0], "count": c[1]} for c in country_counts
    ]

    # 3. Finansallar (Gross MRR & Tahmini Maliyet)
    gross_mrr = sum([Decimal(str(s.subscription_plan_price or 0)) for s in active_stores])
    
    # Shopify Partner komisyonu ($1M'a kadar %0)
    shopify_cut = Decimal("0.00")
    
    # Tahmini Twilio maliyeti (Örnek: Aktif mağaza başına ortalama $3.50 WhatsApp API masrafı)
    estimated_twilio_cost = Decimal(active_stores_count) * Decimal("3.50")
    net_revenue = gross_mrr - shopify_cut - estimated_twilio_cost

    return {
        "summary": {
            "active_stores": active_stores_count,
            "gross_mrr": float(gross_mrr),
            "estimated_twilio_cost": float(estimated_twilio_cost),
            "net_revenue": float(net_revenue)
        },
        "countries": country_breakdown,
        "stores": [
            {
                "id": s.id,
                "shop_domain": s.shop,
                "country": s.country_code,
                "plan_price": float(s.subscription_plan_price),
                "created_at": s.createdAt
            }
            for s in active_stores
        ]
    }
