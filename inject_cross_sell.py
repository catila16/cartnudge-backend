import re

with open('app/api/v1/webhooks/whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Import
if 'ShopifyCrossSellAgent' not in content:
    content = content.replace('from app.services import meta_whatsapp_service, openai_service', 'from app.services import meta_whatsapp_service, openai_service\nfrom app.services.cross_sell_service import ShopifyCrossSellAgent')

# Change to async def
content = content.replace('def process_whatsapp_message(from_number: str, body: str):', 'async def process_whatsapp_message(from_number: str, body: str):')

# Find the block where checkout_url is generated
# Using regex to replace the entire block
pattern = r'# Shopify Cart Permalink.*?(?=history\.append\(\{"role": "user")'
replacement = """# CROSS-SELL (Phase 1)
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

        # 6. Sohbet Geçmişini Güncelle
        """

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('app/api/v1/webhooks/whatsapp.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("whatsapp.py updated.")
