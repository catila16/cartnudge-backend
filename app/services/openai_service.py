import os
from openai import OpenAI

# Initialize OpenAI client
# It automatically picks up the OPENAI_API_KEY environment variable.
client = OpenAI()

def generate_cart_recovery_message(line_items: list) -> str:
    """
    Generates a personalized WhatsApp cart recovery message using OpenAI gpt-4o.
    """
    # If no items are provided or API key is missing (client fails to init properly, though OpenAI() won't crash until used usually, but just in case)
    if not line_items:
        return "Merhaba! CartNudge mağazasında sepetinizde harika ürünler bıraktığınızı fark ettik. Siparişinizi tamamlamak için yardıma ihtiyacınız var mı? Size özel ufak bir sürprizimiz olabilir! 🎁"
    
    # Format the line items into a readable string for the prompt
    item_details = []
    for item in line_items:
        title = item.get("title", "Ürün")
        quantity = item.get("quantity", 1)
        variant_title = item.get("variant_title", "")
        
        detail_str = f"- {quantity}x {title}"
        if variant_title and variant_title != "Default Title":
            detail_str += f" ({variant_title})"
        
        item_details.append(detail_str)
        
    items_str = "\n".join(item_details)
    
    prompt = f"""
Sen, e-ticaret mağazasının çok samimi, yardımsever ve hafif ikna edici bir müşteri temsilcisisin. (Bir satış robotu gibi değil, gerçek bir insan gibi hissettirmelisin).
Müşteri aşağıdaki ürünleri sepetinde unuttu ve satın almadan siteden ayrıldı:

{items_str}

Lütfen bu müşteriye WhatsApp üzerinden gönderilecek kısa, dikkat çekici ve hiper-spesifik bir mesaj yaz.
Kurallar:
1. Müşteriye ürünün adını, rengini/bedenini (eğer belirtilmişse) hatırlat ki mesajın özel yazıldığı belli olsun.
2. Stokların hızlı tükendiğine dair hafif bir aciliyet hissi ver.
3. Onu siparişi tamamlamaya ikna etmek için %10 indirim tanımladığını söyle ve "CART10" kupon kodunu ver.
4. Mesaj çok uzun olmasın (WhatsApp okuma alışkanlıklarına uygun, kısa paragraflar).
5. Emojiler kullan ama abartma.
6. Sadece mesaj metnini döndür, başına sonuna not ekleme.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert e-commerce conversion copywriter writing in Turkish."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=250
        )
        message = response.choices[0].message.content.strip()
        return message
    except Exception as e:
        print(f"OpenAI Error: {e}")
        # Fallback message in case of API failure
        return "Merhaba! Sepetinizdeki ürünlerin sizi beklediğini hatırlatmak istedik. Siparişinizi tamamlamak için 'CART10' koduyla %10 indirim fırsatını kaçırmayın! 🎁"
