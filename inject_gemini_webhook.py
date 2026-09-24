import re

with open('app/api/v1/webhooks/whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Imports
imports_to_add = """from app.services.voice_engine import AntigravityVoiceResolver
from app.services.gemini_agent import gemini_agent
import os
"""
if "AntigravityVoiceResolver" not in content:
    content = content.replace("from app.services.cross_sell_service import ShopifyCrossSellAgent", imports_to_add + "\nfrom app.services.cross_sell_service import ShopifyCrossSellAgent")

# 2. Modify receive_whatsapp_reply to handle Audio and trigger mark_as_read
pattern_receive = r'            for msg in messages:\n                if msg\.get\("type"\) == "text":\n                    from_number = msg\.get\("from"\)\n                    text_body = msg\.get\("text", \{\}\)\.get\("body", ""\)\n                    \n                    logger\.info\(f"Incoming Meta WhatsApp message from \{from_number\}: \{text_body\}"\)\n                    background_tasks\.add_task\(process_whatsapp_message, from_number, text_body\)'

replacement_receive = """            for msg in messages:
                msg_id = msg.get("id")
                if msg_id:
                    # Blue tick!
                    background_tasks.add_task(meta_whatsapp_service.mark_message_as_read, msg_id)
                
                from_number = msg.get("from")
                msg_type = msg.get("type")
                
                if msg_type == "text":
                    text_body = msg.get("text", {}).get("body", "")
                    logger.info(f"Incoming Meta text from {from_number}: {text_body}")
                    background_tasks.add_task(process_whatsapp_message, from_number, text_body)
                elif msg_type == "audio":
                    media_id = msg.get("audio", {}).get("id")
                    logger.info(f"Incoming Meta audio from {from_number}, media_id: {media_id}")
                    # Process audio
                    background_tasks.add_task(process_whatsapp_audio, from_number, media_id)"""

content = re.sub(pattern_receive, replacement_receive, content)

# 3. Add process_whatsapp_audio function which delegates to process_whatsapp_message
process_audio_func = """
async def process_whatsapp_audio(from_number: str, media_id: str):
    try:
        audio_bytes = await meta_whatsapp_service.download_media_bytes(media_id)
        lang_code = get_language_from_phone(from_number.replace("+", "").strip())
        resolver = AntigravityVoiceResolver(openai_api_key=os.getenv("OPENAI_API_KEY"))
        
        if not audio_bytes:
            err_msg = resolver.get_fallback_text(lang_code, "audio_error")
            meta_whatsapp_service.send_whatsapp_message(from_number, err_msg)
            return
            
        res = await resolver.transcribe_voice(audio_bytes, customer_locale=lang_code)
        if not res.get("success") or not res.get("text"):
            err_msg = resolver.get_fallback_text(lang_code, "not_understood")
            meta_whatsapp_service.send_whatsapp_message(from_number, err_msg)
            return
            
        transcribed_text = res["text"]
        logger.info(f"Transcribed audio from {from_number}: {transcribed_text}")
        
        # Now pass to normal message processor
        await process_whatsapp_message(from_number, transcribed_text)
    except Exception as e:
        logger.error(f"process_whatsapp_audio error: {e}")
"""

# Insert process_whatsapp_audio right before receive_whatsapp_reply
content = content.replace('@router.post("/incoming")', process_audio_func + '\n@router.post("/incoming")')

# 4. Modify process_whatsapp_message to use Gemini instead of OpenAI
pattern_gemini = r'        ai_reply = openai_service\.process_negotiation_reply\([\s\S]*?meta_whatsapp_service\.send_whatsapp_message\(from_number, reply_content\)'

replacement_gemini = """        instruction = gemini_agent.build_system_instruction(
            shop_domain=conversation.store_id,
            cart_summary=items_str,
            discount_ceiling=f"%{discount_pct}",
            cross_sell_context=prompt_context,
            customer_language=fallback_language
        )
        
        result = await gemini_agent.execute_turn(
            user_message=body,
            chat_history=history,
            system_instruction=instruction
        )
        
        if result["type"] == "LOST_SALE":
            conversation.status = ConversationStatus.DECLINED
            conversation.lost_sale_category = result.get("category")
            conversation.lost_sale_detail = result.get("detail")
            logger.info(f"Lost sale detected: {conversation.lost_sale_category} - {conversation.lost_sale_detail}")
            reply_content = result.get("farewell_message", "Anlayışla karşılıyoruz, iyi günler dileriz.")
        else:
            reply_content = result.get("reply_text", "Hata oluştu.")
            
        # 6. Sohbet Geçmişini Güncelle
        history.append({"role": "user", "content": body})
        history.append({"role": "assistant", "content": reply_content})
        conversation.chat_history = history
        
        flag_modified(conversation, "chat_history")
        db.commit()

        # 7. Yanıtı Meta API İle Doğrudan Gönder
        meta_whatsapp_service.send_whatsapp_message(from_number, reply_content)"""

content = re.sub(pattern_gemini, replacement_gemini, content)

with open('app/api/v1/webhooks/whatsapp.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("whatsapp.py updated for Gemini and Voice.")
