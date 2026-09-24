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
    ) -> str:
        
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

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add valid history
        for msg in chat_history:
            if isinstance(msg, dict) and msg.get("role") in ["user", "assistant"] and msg.get("content"):
                messages.append(msg)
                
        # Add latest user message
        messages.append({"role": "user", "content": latest_message})

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.6,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return f"Harika bir tercih {customer_name}! Sepetindeki ürünler tükenmeden alışverişini tamamlamak istersen linkin burada: {checkout_url}"

openai_service = OpenAIService()
