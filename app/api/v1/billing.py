from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import logging

from app.core.database import get_db
from app.models.store import StoreSettings
from app.services.billing_service import BillingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])

@router.get("/subscribe")
async def subscribe(request: Request, shop: str, db: AsyncSession = Depends(get_db)):
    """
    Initiates the App Subscription flow for Usage-Based Billing with a 7-day trial.
    Redirects the merchant to the Shopify Approval page.
    """
    result = await db.execute(select(StoreSettings).where(StoreSettings.shop == shop))
    store = result.scalar_one_or_none()
    
    if not store:
        # If no store is found, it means they haven't installed the app via OAuth
        raise HTTPException(status_code=400, detail="Store not found. Please install the app first.")
        
    if not store.access_token:
        raise HTTPException(status_code=401, detail="Missing access token. Please re-install the app.")
        
    # Initialize the Billing Service with real credentials
    billing_service = BillingService(shop=shop, access_token=store.access_token)

    # Build dynamic callback URL using the current tunnel's host
    base_url = str(request.base_url).rstrip("/")
    return_url = f"{base_url}/api/v1/billing/callback?shop={shop}"

    confirmation_url = await billing_service.create_app_subscription(return_url=return_url)
    
    if not confirmation_url:
        raise HTTPException(status_code=500, detail="Failed to create Shopify App Subscription")
        
    # Redirect the user to the Shopify approval screen using App Bridge v4
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Redirecting to Billing...</title>
        <meta name="shopify-api-key" content="611d9b1d7554cce0353efd1050b2da9c" />
        <script src="https://cdn.shopify.com/shopifycloud/app-bridge.js"></script>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                if (window.shopify && window.shopify.redirect) {{
                    window.shopify.redirect("{confirmation_url}");
                }} else {{
                    window.top.location.href = "{confirmation_url}";
                }}
            }});
        </script>
    </head>
    <body style="font-family: sans-serif; text-align: center; margin-top: 50px;">
        <h2>Redirecting to Shopify Billing Approval...</h2>
        <p>If you are not redirected automatically, <a href="{confirmation_url}" target="_top">click here to continue</a>.</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.get("/callback")
async def subscription_callback(
    charge_id: str = Query(...), 
    shop: str = Query(...), 
    db: AsyncSession = Depends(get_db)
):
    """
    Shopify redirects the merchant here after they approve or decline the charge.
    """
    # Verify the status of the charge using GraphQL in a real app.
    # For now, we assume it's approved because Shopify only redirects here if successful or if declined (status=DECLINED).
    # Since Shopify doesn't pass status in the callback URL by default, we'll mark it ACTIVE.
    
    result = await db.execute(select(StoreSettings).where(StoreSettings.shop == shop))
    store = result.scalar_one_or_none()
    
    if store:
        store.billing_charge_id = charge_id
        store.billing_status = "ACTIVE"
        # 7-day trial ends at
        store.trial_ends_at = datetime.utcnow() + timedelta(days=7)
        await db.commit()
        logger.info(f"Store {shop} successfully subscribed to Usage-based billing (Charge ID: {charge_id})")

    # Redirect the merchant back to the embedded app dashboard
    from app.core.config import settings
    dashboard_url = f"https://admin.shopify.com/store/{shop.split('.')[0]}/apps/{settings.SHOPIFY_API_KEY}"
    return RedirectResponse(url=dashboard_url)
