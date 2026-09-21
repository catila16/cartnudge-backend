import os
from celery import Celery
from datetime import datetime, timedelta

# Celery Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("cartnudge_workers", broker=REDIS_URL, backend=REDIS_URL)

# For local testing without Redis, set task_always_eager to True
celery_app.conf.task_always_eager = True

from app.services.twilio_service import twilio_service

@celery_app.task(name="trigger_first_contact")
def trigger_first_contact(
    phone: str, 
    customer_name: str, 
    checkout_url: str, 
    country_code: str = None
):
    """
    Kullanıcıya ilk temas olarak Meta onaylı şablon mesajını gönderir.
    """
    if not phone:
        return {"status": "skipped", "reason": "Telefon numarası bulunamadı"}

    print(f"Triggering first contact via template for: {phone}")

    result = twilio_service.send_whatsapp_template(
        to_phone=phone,
        customer_name=customer_name,
        checkout_url=checkout_url,
        country_code=country_code
    )
    return result

@celery_app.task
def trigger_followup_contact(conversation_id: str):
    """
    24. Saat dolduğunda tetiklenir.
    Eğer sipariş hala kapanmadıysa (NEGOTIATION veya PENDING), 
    son şans indirimi atılır.
    """
    # TODO: Fetch from DB, check status, trigger final offer
    print(f"Triggering 24h follow-up for conversation: {conversation_id}")
    return True

import zoneinfo

def apply_quiet_hours(target_time: datetime, start_str: str, end_str: str) -> tuple[datetime, bool]:
    start_time = datetime.strptime(start_str, "%H:%M").time()
    end_time = datetime.strptime(end_str, "%H:%M").time()
    
    overnight = start_time > end_time
    tt_time = target_time.time()
    
    is_quiet = False
    if overnight:
        if tt_time >= start_time or tt_time <= end_time:
            is_quiet = True
    else:
        if start_time <= tt_time <= end_time:
            is_quiet = True
            
    if is_quiet:
        shifted_time = datetime.combine(target_time.date(), end_time, tzinfo=target_time.tzinfo) + timedelta(minutes=1)
        if overnight and tt_time >= start_time:
            shifted_time += timedelta(days=1)
        return shifted_time, True
        
    return target_time, False

def schedule_cart_recovery(
    conversation_id: str, 
    store_settings: dict = None, 
    customer_phone: str = None, 
    line_items: list = None,
    first_name: str = "Customer",
    checkout_url: str = "",
    country_code: str = None
):
    """
    Shopify'dan checkouts/update geldiğinde bu foksiyon çağrılır.
    """
    if store_settings is None:
        store_settings = {}
        
    # TEMPORARY TEST OVERRIDES
    delay_minutes = 1 # store_settings.get("cartAbandonmentDelay", 60)
    followup_hours = store_settings.get("cartFollowupHours", 24)
    quiet_enabled = False # store_settings.get("quietHoursEnabled", False)
    quiet_start = store_settings.get("quietHoursStart", "22:00")
    quiet_end = store_settings.get("quietHoursEnd", "08:00")
    
    tz_name = store_settings.get("timezone", "UTC")
    try:
        tz = zoneinfo.ZoneInfo(tz_name)
    except Exception:
        tz = zoneinfo.ZoneInfo("UTC")

    now_utc = datetime.now(zoneinfo.ZoneInfo("UTC"))
    now_local = now_utc.astimezone(tz)
    
    original_target_1 = now_local + timedelta(minutes=delay_minutes)
    
    final_target_1, shifted_1 = original_target_1, False
    if quiet_enabled:
        final_target_1, shifted_1 = apply_quiet_hours(original_target_1, quiet_start, quiet_end)
    
    countdown_1 = int((final_target_1 - now_local).total_seconds())
    if countdown_1 < 0: countdown_1 = 0
    
    if shifted_1:
        print(f"[SCHEDULER] Original: {original_target_1.strftime('%H:%M')} -> Shifted: {final_target_1.strftime('%b %d, %H:%M')} ({tz_name}) | Reason: Quiet Hours")
    else:
        print(f"[SCHEDULER] Cart recovery task scheduled for {final_target_1.strftime('%H:%M')} ({tz_name})")

    # Schedule first contact
    trigger_first_contact.apply_async(
        args=[customer_phone, first_name, checkout_url, country_code], 
        countdown=countdown_1
    )
    
    # Schedule 24h follow-up
    trigger_followup_contact.apply_async(
        args=[conversation_id], 
        countdown=followup_hours * 3600
    )
    
    return True
