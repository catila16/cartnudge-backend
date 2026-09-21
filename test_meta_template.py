import os
import requests

# Test etmek için .env verilerini veya aşağıdaki değişkenleri doldurun.
META_ACCESS_TOKEN = os.getenv("META_WA_PERMANENT_ACCESS_TOKEN", "EAAPzVssr4vABSpldA1AOna7ExAaeP9ba7e9ZBRInOoDClIhpkNpUTya8JirriBJpc8WQxTQmyzCEnQ8ru8PmafP9ECjrir69P0OnQ6DsVrKGCCRpNiAahMH6bYQZASQU3qiDBUxb2ZAuwVh4uSGZANom7egf2o6kYaN7MCo9Dk0GK34xsEpMdy8hsRAsDQZDZD")
META_PHONE_NUMBER_ID = os.getenv("META_WA_PHONE_NUMBER_ID", "1400018353184513")
TEMPLATE_NAME = "abandoned_cart_alert"

# Test mesajının gideceği kendi numaranızı yazın (Örn: 905321234567, başında + olmadan)
TEST_RECIPIENT = "905345900476"

def detect_language_code(phone: str) -> str:
    # Basit bir dil yönlendirmesi
    if phone.startswith("90"):
        return "tr"
    elif phone.startswith("49") or phone.startswith("43") or phone.startswith("41"):
        return "de"
    return "en_US"

def send_test_template():
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("❌ Lütfen META_WA_PERMANENT_ACCESS_TOKEN ve META_WA_PHONE_NUMBER_ID değerlerini girin.")
        return

    url = f"https://graph.facebook.com/v18.0/{META_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    lang_code = detect_language_code(TEST_RECIPIENT)

    payload = {
        "messaging_product": "whatsapp",
        "to": TEST_RECIPIENT,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {
                "code": lang_code
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": "Ahmet"},                   # {{1}} Müşteri Adı
                        {"type": "text", "text": "MyStore"},                 # {{2}} Mağaza Adı
                        {"type": "text", "text": "https://mystore.com/123"}  # {{3}} Link
                    ]
                }
            ]
        }
    }

    print(f"🚀 Meta Cloud API'ye istek gönderiliyor (Dil: {lang_code})...")
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("✅ Başarılı! Mesaj gönderildi. Gelen yanıt:")
        print(response.json())
    else:
        print(f"❌ Hata ({response.status_code}):")
        print(response.text)

if __name__ == "__main__":
    send_test_template()
