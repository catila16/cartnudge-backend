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

@router.post("/checkouts/update")
async def shopify_checkout_update(request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Webhook endpoint for Shopify checkouts/update.
    """
    payload_data = await request.json()
    
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
            
        # Extract line items for OpenAI personalization
        line_items = checkout.get("line_items", [])
            
        # We delegate the delay logic to Celery
        print(f"Checkout update received: {checkout_token}. Scheduling recovery...")
        
        # Upsert conversation in database
        stmt = select(Conversation).where(Conversation.id == checkout_token)
        result = await db.execute(stmt)
        conversation = result.scalars().first()
        
        if not conversation:
            cart_value = total_price
            items_summary = ", ".join([f"{item.get('quantity', 1)}x {item.get('title', 'Item')}" for item in line_items])
            conversation = Conversation(
                id=checkout_token,
                customer_phone=customer_phone,
                cart_value=cart_value,
                items_summary=items_summary,
                status="PENDING",
                store_id="cartnudge-test"
            )
            db.add(conversation)
            await db.commit()
        
        schedule_cart_recovery(
            conversation_id=checkout_token, 
            store_settings=store_settings,
            customer_phone=customer_phone,
            line_items=line_items
        )
        
    return {"status": "ok"}
