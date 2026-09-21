import requests

WEBHOOK_URL = "http://127.0.0.1:8000/api/v1/webhooks/whatsapp/incoming"

data = {
    "From": "whatsapp:+905345900476",  # Kendi numaran
    "Body": "Fiyatlar biraz yüksek, indirim var mı?"  # Mock asistanı tetikleyecek mesaj
}

print(f"Twilio simülasyonu başlatılıyor...")
print(f"Gönderilen Mesaj: '{data['Body']}'")

try:
    response = requests.post(WEBHOOK_URL, data=data)
    print(f"Sunucu Yanıtı: {response.status_code}")
    print("Mükemmel! Arka planda sunucu bu mesajı işleyip sana WhatsApp'tan mock yanıtı atmış olmalı.")
except Exception as e:
    print(f"Hata: {e}")
