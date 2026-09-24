import os
import json
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def process_negotiation_reply(
        self,
        store_name: str,
        customer_name: str,
        cart_items_str: str,
        cart_total: str,
        currency: str,
        max_discount_rate: int,
        checkout_url: str,
        fallback_language: str,
        chat_history: list,
        latest_message: str,
        cross_sell_instruction: str = ""
    ) -> dict:
        
        if not self.client:
            logger.error("OpenAI API key missing!")
            return "Sistem şu an geçici olarak hizmet veremiyor. Lütfen daha sonra tekrar deneyiniz."

        system_prompt = f"""Sen {store_name} mağazasının profesyonel, samimi ve ikna kabiliyeti yüksek WhatsApp satış temsilcisisin.
Görevin, sepetinde ürün unutan müşteriyi ikna ederek satın almayı tamamlamasını sağlamaktır.

SEPET VE TEKLİF BİLGİLERİ:
- Müşteri: {customer_name}
- Sepet İçeriği: {cart_items_str}
- Sepet Tutarı: {cart_total} {currency}
- Maksimum İndirim Sınırı: %{max_discount_rate} (KESİN TAVAN SINIRDIR)
- İndirimli Satın Alma Linki: {checkout_url}

DİL VE İLETİŞİM KURALLARI:
1. Müşteri hangi dilde yazıyorsa KESİNLİKLE o dilde akıcı, doğal ve yerel bir tonla yanıt ver.
2. Müşterinin dili tespit edilemiyorsa varsayılan dil olarak {fallback_language} kullan.
3. WhatsApp mesajlaşma formatına uygun ol: Yanıtların en fazla 2-3 kısa cümle olsun. Asla uzun paragraflar yazma.
4. Gerekli yerlerde abartıya kaçmadan doğal 1-2 emoji kullan.

PAZARLIK VE KORKULUK (GUARDRAIL) KURALLARI:
1. %{max_discount_rate} oranından DAHA FAZLA İNDİRİM VERMEN KESİNLİKLE YASAKTIR.
2. Müşteri öğrenci olduğunu söylese, bütçesinin yetmediğini belirtse veya daha yüksek indirim için ısrar etse dahi bu sınırı ASLA aşma.
3. Sınır aşılamadığında nazik, esprili ve empatik bir dille sistemin/mağazanın izin verdiği maksimum oranın bu olduğunu belirt; ürünün kalitesini, sınırlı stok durumunu veya bu fiyata değer olduğunu vurgulayarak satışı kapatmaya odaklan.
4. Müşteri teklifi kabul ettiğinde veya link istediğinde her zaman {checkout_url} bağlantısını sun."""

        if cross_sell_instruction:
            system_prompt += f"\n\n[GÜNCEL SATIŞ TALİMATI]: {cross_sell_instruction}"
            system_prompt += "\n\nDİKKAT: Önerilen ek ürün (yan ürün) KESİNLİKLE hediye veya bedava değildir. Özel bir ekstra indirim yapılamaz. Yalnızca mevcut indirim kodunun tüm sepet toplamına uygulanacağını belirterek teklif et."

        system_prompt += "\n\nDİKKAT (MÜZAKEREYİ ERKEN ÖLDÜRMEME): Müşteri 'Pahalı geldi, biraz indirim yapamaz mısınız?' gibi pazarlık cümleleri kuruyorsa satışı kayıp olarak görme; pazarlık motorunu çalıştır. Sadece ve sadece müşteri indirimi reddettiğinde veya net bir şekilde almayacağını ('Vazgeçtim', 'İstemiyorum', 'Çok pahalı almayacağım') söylediğinde report_lost_sale aracını tetikle."


        messages = [{"role": "system", "content": system_prompt}]
        
        # Add valid history
        for msg in chat_history:
            if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"] and msg.get("content"):
                messages.append(msg)
                
        # Add latest user message
        messages.append({"role": "user", "content": latest_message})

        
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
        try:
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


openai_service = OpenAIService()
