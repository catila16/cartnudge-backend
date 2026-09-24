import json

with open('app/services/openai_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update signature to return dict
content = content.replace(') -> str:', ') -> dict:')

# 2. Add Guardrail to System Prompt
guardrail = """
        system_prompt += "\\n\\nDİKKAT (MÜZAKEREYİ ERKEN ÖLDÜRMEME): Müşteri 'Pahalı geldi, biraz indirim yapamaz mısınız?' gibi pazarlık cümleleri kuruyorsa satışı kayıp olarak görme; pazarlık motorunu çalıştır. Sadece ve sadece müşteri indirimi reddettiğinde veya net bir şekilde almayacağını ('Vazgeçtim', 'İstemiyorum', 'Çok pahalı almayacağım') söylediğinde report_lost_sale aracını tetikle."
"""
if "MÜZAKEREYİ ERKEN ÖLDÜRMEME" not in content:
    content = content.replace('belirterek teklif et."', 'belirterek teklif et."\n' + guardrail)

# 3. Add tools definition and tool_choice
tools_def = """
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "report_lost_sale",
                    "description": "Müşteri satışı kesin olarak reddettiğinde, vazgeçtiğinde veya ilgilenmediğini belirttiğinde çağrılır. Müzakere sürüyorsa (örn: 'indirim var mı?' diyorsa) ASLA çağrılmaz.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": ["PRICE_TOO_HIGH", "SHIPPING_COST", "SHIPPING_TIME", "COMPETITOR", "POSTPONED", "NOT_INTERESTED", "OTHER"],
                                "description": "Kaybın ana nedeni."
                            },
                            "detail": {
                                "type": "string",
                                "description": "Müşterinin vazgeçme gerekçesinin 1-2 cümlelik net Türkçe özeti."
                            },
                            "farewell_message": {
                                "type": "string",
                                "description": "Müşteriye WhatsApp'tan gönderilecek son derece nazik, anlayışlı, kapıyı açık bırakan veda mesajı."
                            }
                        },
                        "required": ["category", "detail", "farewell_message"]
                    }
                }
            }
        ]
"""

# Replace the chat completions call by splitting at "try:"
parts = content.split("try:")

new_call = tools_def + """        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.6,
                max_tokens=300,
                tools=tools
            )
            
            message = response.choices[0].message
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    if tool_call.function.name == "report_lost_sale":
                        args = json.loads(tool_call.function.arguments)
                        return {
                            "type": "tool",
                            "category": args.get("category"),
                            "detail": args.get("detail"),
                            "content": args.get("farewell_message", "Anlayışla karşılıyoruz, iyi günler dileriz.")
                        }
            
            return {"type": "text", "content": message.content.strip() if message.content else "Tamamdır, iyi günler!"}
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return {"type": "text", "content": f"Harika bir tercih {customer_name}! Sepetindeki ürünler tükenmeden alışverişini tamamlamak istersen linkin burada: {checkout_url}"}
"""

content = parts[0] + new_call

with open('app/services/openai_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("openai_service.py updated with Function Calling.")
