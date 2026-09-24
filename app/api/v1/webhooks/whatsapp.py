from app.services.cross_sell_service import ShopifyCrossSellAgent
import os
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, BackgroundTasks, Response, Query, HTTPException
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.conversation import Conversation, ConversationStatus
from app.models.store import StoreSettings
from app.services.openai_service import openai_service
from app.services.meta_whatsapp_service import meta_whatsapp_service
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter()
logger = logging.getLogger(__name__)

# OPT-OUT KEYWORDS
OPT_OUT_KEYWORDS = {
    "en": ["stop", "unsubscribe", "cancel", "quit", "end", "optout", "opt-out"],
    "tr": ["iptal", "dur", "istemiyorum", "mesaj atma", "engelle", "çıkış", "cikis"],
    "de": ["stopp", "abmelden", "beenden", "aufhören", "aufhoren", "keine nachrichten"],
    "fr": ["arret", "arrêter", "arreter", "stop", "désabonner", "desabonner", "non merci"],
    "es": ["baja", "parar", "cancelar", "no quiero"],
    "it": ["ferma", "cancella", "disiscriviti"]
}

OPT_OUT_RESPONSES = {
    "tr": "Tercihinize saygı duyuyoruz, size bir daha mesaj gönderilmeyecektir.",
    "de": "Wir respektieren Ihre Entscheidung. Sie werden keine weiteren Nachrichten erhalten.",
    "fr": "Nous respectons votre choix. Vous ne recevrez plus de messages.",
    "es": "Respetamos su elección. No recibirá más mensajes.",
    "it": "Rispettiamo la tua scelta. Non riceverai ulteriori messaggi.",
    "en": "We respect your choice. You will not receive any further messages."
}

def get_language_from_phone(phone: str) -> str:
    if phone.startswith("90"): return "tr"
    if phone.startswith("49") or phone.startswith("43") or phone.startswith("41"): return "de"
    if phone.startswith("33") or phone.startswith("32"): return "fr"
    if phone.startswith("34"): return "es"
    if phone.startswith("39"): return "it"
    return "en"

async def process_whatsapp_message(from_number: str, body: str):
    db: Session = SessionLocal()
    try:
        clean_phone = from_number.replace("+", "").strip()
        lang_code = get_language_from_phone(clean_phone)
        
        # 1. OPT-OUT (GLOBAL FILTER)
        # Handle Turkish upper I/İ issues before lower()
        msg_clean = body.strip().replace('I', 'ı').replace('İ', 'i').lower()
        is_opt_out = False
        for lang, words in OPT_OUT_KEYWORDS.items():
            if any(word in msg_clean for word in words):
                is_opt_out = True
                break
                
        # Aktif konuşmayı bul
        conversation = db.query(Conversation).filter(
            Conversation.customer_phone.like(f"%{clean_phone[-10:]}"),
            Conversation.status.in_([ConversationStatus.PENDING, ConversationStatus.NEGOTIATION])
        ).order_by(Conversation.scheduled_at.desc()).first()

        if not conversation:
            logger.warning(f"No active conversation found for {from_number}")
            return

        if is_opt_out:
            logger.info(f"Opt-out detected for {clean_phone}. Closing conversation.")
            conversation.status = ConversationStatus.DECLINED
            db.commit()
            goodbye_msg = OPT_OUT_RESPONSES.get(lang_code, OPT_OUT_RESPONSES["en"])
            meta_whatsapp_service.send_whatsapp_message(from_number, goodbye_msg)
            return

        now = datetime.now(timezone.utc)

        # 2. 24 Saatlik Pencere Kontrolü
        if conversation.last_customer_message_at:
            last_msg_time = conversation.last_customer_message_at
            if last_msg_time.tzinfo is None:
                last_msg_time = last_msg_time.replace(tzinfo=timezone.utc)
                
            elapsed = now - last_msg_time
            if elapsed > timedelta(hours=24):
                logger.warning("[Meta Violation Guard] 24 saatlik müşteri penceresi kapandı.")
                return

        conversation.last_customer_message_at = now
        conversation.status = ConversationStatus.NEGOTIATION
        
        history = conversation.chat_history
        if not isinstance(history, list):
            history = []
        
        # Mağaza Ayarları
        store = db.query(StoreSettings).filter(StoreSettings.shop == conversation.store_id).first()
        discount_pct = store.maxDiscountMargin if store and store.maxDiscountMargin else 15

        # Veri Çıkarımı
        cart_data = conversation.cart_data if isinstance(conversation.cart_data, dict) else {}
        line_items = cart_data.get("line_items", [])
        
        cart_total_val = 0
        items_str = ""
        variant_strings = []
        
        for item in line_items:
            price = float(item.get("price", 0))
            qty = int(item.get("quantity", 1))
            cart_total_val += (price * qty)
            title = item.get("title", "Ürün")
            items_str += f"- {qty}x {title} ({price})\n"
            
            variant_id = item.get("variant_id")
            # Fallback for seed data which doesn't have variant_id
            if not variant_id:
                variant_id = "123456" # fallback for testing
            variant_strings.append(f"{variant_id}:{qty}")
        
        currency = cart_data.get("currency", "TRY")
        
        # CROSS-SELL (Phase 1)
        cross_sell_agent = ShopifyCrossSellAgent(shop_domain=conversation.store_id, access_token="mock_token")
        cross_sell_data = await cross_sell_agent.get_smart_cross_sell(
            cart_items=line_items,
            discount_code=f"NUDGE{discount_pct}",
            max_ratio=0.25
        )
        
        # Görev 5: DB Log Analytics
        if cross_sell_data.get("has_upsell") and cross_sell_data.get("offered_variant_id"):
            conversation.offered_cross_sell_variant_id = cross_sell_data["offered_variant_id"]
            
        checkout_url = cross_sell_data.get("checkout_url")
        prompt_context = cross_sell_data.get("prompt_context", "")
            
        fallback_language = {"tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "fr": "Fransızca", "es": "İspanyolca", "it": "İtalyanca"}.get(lang_code, "İngilizce")

        ai_reply = openai_service.process_negotiation_reply(
            store_name=conversation.store_id,
            customer_name="Değerli Müşterimiz",
            cart_items_str=items_str,
            cart_total=f"{cart_total_val:.2f}",
            currency=currency,
            max_discount_rate=discount_pct,
            checkout_url=checkout_url,
            fallback_language=fallback_language,
            chat_history=history,
            latest_message=body,
            cross_sell_instruction=prompt_context
        )
        reply_content = ai_reply.get("content", "Anlayışla karşılıyoruz, iyi günler dileriz.") if isinstance(ai_reply, dict) else ai_reply
        
        # Görev 7: Kayıp Satış Analizi İşlemi
        if isinstance(ai_reply, dict) and ai_reply.get("type") == "tool":
            conversation.status = ConversationStatus.DECLINED
            conversation.lost_sale_category = ai_reply.get("category")
            conversation.lost_sale_detail = ai_reply.get("detail")
            logger.info(f"Lost sale detected: {conversation.lost_sale_category} - {conversation.lost_sale_detail}")

        # 6. Sohbet Geçmişini Güncelle
        history.append({"role": "user", "content": body})
        history.append({"role": "assistant", "content": reply_content})
        conversation.chat_history = history
        
        flag_modified(conversation, "chat_history")
        db.commit()

        # 7. Yanıtı Meta API İle Doğrudan Gönder
        meta_whatsapp_service.send_whatsapp_message(from_number, reply_content)

    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}")
        db.rollback()
    finally:
        db.close()


@router.get("/incoming")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    verify_token = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "cartnudge_secret")
    
    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info("Meta webhook verified successfully.")
        return Response(content=hub_challenge, media_type="text/plain")
        
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/incoming")
async def receive_whatsapp_reply(
    request: Request,
    background_tasks: BackgroundTasks
):
    try:
        body = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    if body.get("object") != "whatsapp_business_account":
        return Response(status_code=404)

    entries = body.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            
            for msg in messages:
                if msg.get("type") == "text":
                    from_number = msg.get("from")
                    text_body = msg.get("text", {}).get("body", "")
                    
                    logger.info(f"Incoming Meta WhatsApp message from {from_number}: {text_body}")
                    background_tasks.add_task(process_whatsapp_message, from_number, text_body)

    return {"status": "ok"}
