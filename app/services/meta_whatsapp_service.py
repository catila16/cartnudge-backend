import os
import requests
import httpx
import json
import phonenumbers

class MetaWhatsAppService:
    def __init__(self):
        self.access_token = os.getenv("META_WA_PERMANENT_ACCESS_TOKEN")
        self.phone_number_id = os.getenv("META_WA_PHONE_NUMBER_ID")
        self.default_template_name = os.getenv("META_TEMPLATE_NAME", "abandoned_cart_alert")
        
    def detect_language(self, phone_number: str, country_code: str = None) -> str:
        """
        Ülke kodu veya telefon numarasından Meta'nın kabul edeceği dil kodunu tespit eder.
        """
        if country_code:
            code = country_code.upper()
            if code in ["TR"]: return "tr"
            if code in ["DE", "AT", "CH"]: return "de"

        try:
            parsed = phonenumbers.parse(phone_number, None)
            region = phonenumbers.region_code_for_number(parsed)
            if region == "TR": return "tr"
            if region in ["DE", "AT", "CH"]: return "de"
        except Exception:
            pass

        return "en_US"  # Meta için global/İngilizce varsayılan

    def format_to_e164_without_plus(self, phone_number: str) -> str:
        """
        Meta API, E.164 formatını istiyor ancak başında '+' işareti OLMADAN.
        """
        try:
            parsed = phonenumbers.parse(phone_number, None)
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return formatted.lstrip("+")
        except Exception:
            # Fallback (temizlik)
            cleaned = "".join(filter(str.isdigit, phone_number))
            return cleaned

    def send_whatsapp_template(
        self, 
        to_phone: str, 
        customer_name: str,
        store_name: str,
        checkout_url: str, 
        country_code: str = None,
        template_name: str = None
    ) -> dict:
        """
        Meta Cloud API üzerinden ilk (kanca) şablon mesajını fırlatır.
        """
        if not self.access_token or not self.phone_number_id:
            print("[Meta Dry-Run] Token veya Phone ID eksik. Mesaj simüle edildi.")
            return {"status": "simulated", "to": to_phone}

        clean_number = self.format_to_e164_without_plus(to_phone)
        lang_code = self.detect_language(f"+{clean_number}", country_code)
        
        tpl_name = template_name or self.default_template_name

        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": clean_number,
            "type": "template",
            "template": {
                "name": tpl_name,
                "language": {
                    "code": lang_code
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": customer_name or "Müşteri"},
                            {"type": "text", "text": store_name or "Mağaza"},
                            {"type": "text", "text": checkout_url}
                        ]
                    }
                ]
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()
            
            if response.status_code in (200, 201):
                msg_id = data.get("messages", [{}])[0].get("id", "")
                return {"status": "success", "sid": msg_id, "state": "sent"}
            else:
                print(f"[Meta Error] {data}")
                return {"status": "error", "message": str(data)}
        except Exception as e:
            print(f"[Meta Exception] {str(e)}")
            return {"status": "error", "message": str(e)}

    def send_whatsapp_message(self, to_phone: str, message: str) -> dict:
        """
        Meta kuralları gereği müşteri cevap verdikten sonra 24 saat içinde 
        serbest metin (free-form) mesaj göndermek için kullanılır (OpenAI çıktıları).
        """
        if not self.access_token or not self.phone_number_id:
            print(f"[Meta Dry-Run] Text Message | Body: {message}")
            return {"status": "simulated", "to": to_phone, "body": message}

        clean_number = self.format_to_e164_without_plus(to_phone)
        
        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": clean_number,
            "type": "text",
            "text": {
                "body": message
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()
            
            if response.status_code in (200, 201):
                msg_id = data.get("messages", [{}])[0].get("id", "")
                return {"status": "success", "sid": msg_id, "state": "sent"}
            else:
                print(f"[Meta Error] {data}")
                return {"status": "error", "message": str(data)}
        except Exception as e:
            print(f"[Meta Exception] {str(e)}")
            return {"status": "error", "message": str(e)}


    async def mark_message_as_read(self, message_id: str) -> None:
        if not self.access_token or not self.phone_number_id:
            return
            
        url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(url, headers=headers, json=payload, timeout=5.0)
        except Exception:
            pass

    async def download_media_bytes(self, media_id: str) -> bytes:
        if not self.access_token:
            return None
            
        # 1. Get Media URL
        url = f"https://graph.facebook.com/v18.0/{media_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=headers, timeout=5.0)
                if resp.status_code != 200:
                    print(f"[Meta Media Error] Failed to get media url: {resp.text}")
                    return None
                
                media_url = resp.json().get("url")
                if not media_url:
                    return None
                    
                # 2. Download actual bytes with the SAME auth header (CDN Trap)
                download_resp = await client.get(media_url, headers=headers, timeout=10.0)
                if download_resp.status_code == 200:
                    return download_resp.content
                else:
                    print(f"[Meta Download Error] Status {download_resp.status_code}")
                    return None
                
        except Exception as e:
            print(f"[Meta Download Exception] {e}")
            return None

# Singleton instance
meta_whatsapp_service = MetaWhatsAppService()
