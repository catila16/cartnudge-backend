import re

with open('app/api/v1/webhooks/whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace how ai_reply is handled
pattern = r'(ai_reply = openai_service\.process_negotiation_reply\(.*?cross_sell_instruction=prompt_context\n\s*\))\s*# 6\. Sohbet Geçmişini Güncelle\s*history\.append\(\{"role": "user", "content": body\}\)\s*history\.append\(\{"role": "assistant", "content": ai_reply\}\)\s*conversation\.chat_history = history\s*flag_modified\(conversation, "chat_history"\)\s*db\.commit\(\)\s*# 7\. Yanıtı Meta API İle Doğrudan Gönder\s*meta_whatsapp_service\.send_whatsapp_message\(from_number, ai_reply\)'

replacement = r"""\1
        
        reply_content = ai_reply.get("content", "Anlayışla karşılıyoruz, iyi günler dileriz.")
        
        # Görev 7: Kayıp Satış Analizi İşlemi
        if ai_reply.get("type") == "tool":
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
        meta_whatsapp_service.send_whatsapp_message(from_number, reply_content)"""

# Handle encoding differences in python replace by doing split instead
parts = content.split('cross_sell_instruction=prompt_context\n        )')
if len(parts) == 2:
    part1 = parts[0] + 'cross_sell_instruction=prompt_context\n        )'
    
    # find the end of the block we want to replace
    part2 = parts[1]
    part2 = part2.split('except Exception as e:')[1]
    
    new_block = """
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

    except Exception as e:"""
    
    content = part1 + new_block + part2

with open('app/api/v1/webhooks/whatsapp.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("whatsapp.py updated for Lost Sale Analysis.")
