from fastapi import APIRouter, Request, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.workers.cart_scheduler import schedule_cart_recovery
from app.core.database import get_db
from app.models.conversation import Conversation

router = APIRouter()

# Simple in-memory cache for idempotency during local development
from cachetools import TTLCache
_scheduled_checkouts = TTLCache(maxsize=1000, ttl=3600) # 1 hour TTL

import json
from app.core.security import verify_shopify_hmac

@router.post("/checkouts/create")
@router.post("/checkouts/update")
async def shopify_checkout_update(
    request: Request, 
    background_tasks: BackgroundTasks, 
    db: AsyncSession = Depends(get_db),
    raw_body: bytes = Depends(verify_shopify_hmac)
):
    """
    Webhook endpoint for Shopify checkouts/update.
    """
    payload_data = json.loads(raw_body.decode("utf-8"))
    
    # Shopify checkouts/update webhook sends the checkout directly as the root JSON object
    checkout = payload_data if "token" in payload_data else payload_data.get("checkout", {})
    store_settings = payload_data.get("store_settings", {})
    
    checkout_token = checkout.get("token")
    
    # Safely cast total_price to float
    try:
        total_price = float(checkout.get("total_price", 0))
    except ValueError:
        total_price = 0.0

    min_cart_amount = store_settings.get("minCartAmount", 30)
    
    # In a real app, verify HMAC here
    
    if checkout_token:
        # Guardrail: Check Minimum Cart Amount
        if total_price < min_cart_amount:
            print(f"Checkout {checkout_token} total (${total_price}) is below minimum (${min_cart_amount}). Aborting.")
            return {"status": "ignored", "reason": "ABORTED_BELOW_MIN_CART"}

        # Idempotency check: prevent duplicate webhooks for the same checkout
        if checkout_token in _scheduled_checkouts:
            print(f"Checkout {checkout_token} is already scheduled. Ignoring duplicate webhook.")
            return {"status": "ignored", "reason": "idempotency"}
            
        _scheduled_checkouts[checkout_token] = True
        
        # Extract customer phone from checkout payload
        customer_phone = checkout.get("phone")
        if not customer_phone and checkout.get("shipping_address"):
            customer_phone = checkout.get("shipping_address", {}).get("phone")
        if not customer_phone and checkout.get("customer"):
            customer_phone = checkout.get("customer", {}).get("phone")
            
        # Fallback to test number for sanity testing if Shopify omits it from checkout
        if not customer_phone:
            customer_phone = "+905345900476"
            
        # Extract extra info for templates
        customer = checkout.get("customer") or {}
        first_name = customer.get("first_name") or checkout.get("shipping_address", {}).get("first_name", "Valued Customer")
        checkout_url = checkout.get("abandoned_checkout_url", "")
        country_code = checkout.get("shipping_address", {}).get("country_code")
            
        # Extract line items for OpenAI personalization
        line_items = checkout.get("line_items", [])
            
        # We delegate the delay logic to Celery
        print(f"Checkout update received: {checkout_token}. Scheduling recovery...")
        
        # Upsert conversation in database
        stmt = select(Conversation).where(Conversation.id == checkout_token)
        result = await db.execute(stmt)
        conversation = result.scalars().first()
        
        if not conversation:
            import datetime
            conversation = Conversation(
                id=checkout_token,
                customer_phone=customer_phone,
                cart_data={"total_price": total_price, "line_items": line_items},
                status="PENDING",
                store_id="cartnudge-test",
                scheduled_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=store_settings.get("cartAbandonmentDelay", 15))
            )
            db.add(conversation)
            await db.commit()
        
        schedule_cart_recovery(
            conversation_id=checkout_token, 
            store_settings=store_settings,
            customer_phone=customer_phone,
            line_items=line_items,
            first_name=first_name,
            checkout_url=checkout_url,
            country_code=country_code
        )
        
    return {"status": "ok"}

@router.post("/orders/create")
async def shopify_order_create(
    request: Request, 
    db: AsyncSession = Depends(get_db),
    raw_body: bytes = Depends(verify_shopify_hmac)
):
    """
    Webhook endpoint for Shopify orders/create.
    This is where we process successful conversions and bill the merchant.
    """
    payload_data = json.loads(raw_body.decode("utf-8"))
    order = payload_data
    
    # In Shopify, an order created from a checkout retains the checkout_token
    checkout_token = order.get("checkout_token")
    if not checkout_token:
        return {"status": "ignored", "reason": "No checkout_token"}

    # Find the conversation
    stmt = select(Conversation).where(Conversation.id == checkout_token)
    result = await db.execute(stmt)
    conversation = result.scalars().first()

    if not conversation:
        return {"status": "ignored", "reason": "No related conversation found"}

    # Get the store settings
    store_result = await db.execute(select(StoreSettings).where(StoreSettings.shop == "default.myshopify.com"))
    store = store_result.scalar_one_or_none()

    if not store or store.billing_status != "ACTIVE":
        return {"status": "ignored", "reason": "Store not found or billing not active"}

    total_price = float(order.get("total_price", 0))
    
    # Determine Commission Rate
    rate = 0
    if conversation.conversion_type == "ASSISTED":
        rate = store.assisted_commission_rate # 4%
    elif conversation.status.value in ["SUCCESS", "NEGOTIATION"]:
        # AI recovered
        rate = store.bot_commission_rate # 12%
        conversation.conversion_type = "AI"

    if rate > 0:
        commission_amount = float(total_price) * (float(rate) / 100)
        
        # Charge the merchant via Shopify Billing API
        from app.services.billing_service import BillingService
        billing_service = BillingService(store.shop, access_token=store.access_token)
        
        success = await billing_service.create_usage_charge(
            subscription_id=store.billing_charge_id,
            amount=commission_amount,
            description=f"CartNudge Commission ({rate}%) for Order #{order.get('order_number')}"
        )
        
        if success:
            conversation.status = "SUCCESS"
            conversation.total_recovered_amount = total_price
            conversation.commission_earned = commission_amount
            await db.commit()
            return {"status": "ok", "billed_amount": commission_amount}

    return {"status": "ignored", "reason": "Not a billable conversion"}

from datetime import datetime, timezone
from app.models.store import StoreSettings

@router.post("/app/uninstalled")
async def shopify_app_uninstalled(
    request: Request,
    db: AsyncSession = Depends(get_db),
    raw_body: bytes = Depends(verify_shopify_hmac)
):
    """
    Webhook endpoint for Shopify app/uninstalled.
    Triggered when a merchant uninstalls the app.
    """
    shop_domain = request.headers.get("x-shopify-shop-domain")
    
    if not shop_domain:
        return {"status": "ignored", "reason": "Missing shop domain header"}

    # Find the store and mark as inactive
    stmt = select(StoreSettings).where(StoreSettings.shop == shop_domain)
    result = await db.execute(stmt)
    store = result.scalar_one_or_none()

    if store:
        store.is_active = False
        store.uninstalled_at = datetime.now(timezone.utc)
        store.billing_status = "CANCELLED"
        store.access_token = None # Remove revoked token
        await db.commit()
        print(f"App uninstalled for {shop_domain}. Marked as inactive.")

    return {"status": "ok"}

# ==========================================
# GDPR MANDATORY WEBHOOKS
# ==========================================

@router.post("/customers/data_request")
async def customers_data_request(
    request: Request,
    raw_body: bytes = Depends(verify_shopify_hmac)
):
    """
    Shopify mandatory GDPR webhook.
    Fired when a store owner requests data for a customer.
    Since we don't store long-term raw PII outside of active carts, we return 200 OK.
    """
    payload_data = json.loads(raw_body.decode("utf-8"))
    shop_domain = payload_data.get("shop_domain")
    customer = payload_data.get("customer", {})
    print(f"[GDPR] Data request received for customer {customer.get('id')} at {shop_domain}")
    
    return {"status": "ok"}

@router.post("/customers/redact")
async def customers_redact(
    request: Request,
    db: AsyncSession = Depends(get_db),
    raw_body: bytes = Depends(verify_shopify_hmac)
):
    """
    Shopify mandatory GDPR webhook.
    Fired when a store owner requests to delete customer data.
    """
    payload_data = json.loads(raw_body.decode("utf-8"))
    shop_domain = payload_data.get("shop_domain")
    customer = payload_data.get("customer", {})
    phone = customer.get("phone")
    
    print(f"[GDPR] Redact request received for customer {customer.get('id')} at {shop_domain}")
    
    # Example anonymization: If we had a direct customer table, we would delete it.
    # We will look for conversations matching this phone and redact it.
    if phone:
        stmt = select(Conversation).where(Conversation.customer_phone == phone)
        result = await db.execute(stmt)
        conversations = result.scalars().all()
        for conv in conversations:
            conv.customer_phone = "[REDACTED]"
            if isinstance(conv.cart_data, dict):
                conv.cart_data["redacted"] = True
        await db.commit()
    
    return {"status": "ok"}

@router.post("/shop/redact")
async def shop_redact(
    request: Request,
    db: AsyncSession = Depends(get_db),
    raw_body: bytes = Depends(verify_shopify_hmac)
):
    """
    Shopify mandatory GDPR webhook.
    Fired exactly 48 hours after a store uninstalls the app.
    We must purge all store data from our database.
    """
    payload_data = json.loads(raw_body.decode("utf-8"))
    shop_domain = payload_data.get("shop_domain")
    
    print(f"[GDPR] Shop redact request received for shop {shop_domain}")
    
    # Delete the StoreSettings record
    if shop_domain:
        stmt = select(StoreSettings).where(StoreSettings.shop == shop_domain)
        result = await db.execute(stmt)
        store = result.scalar_one_or_none()
        if store:
            await db.delete(store)
            await db.commit()
            print(f"[GDPR] Deleted store data for {shop_domain}")
            
    return {"status": "ok"}
