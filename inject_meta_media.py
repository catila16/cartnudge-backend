import re

with open('app/services/meta_whatsapp_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_methods = """
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
            requests.post(url, headers=headers, json=payload, timeout=5)
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
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                print(f"[Meta Media Error] Failed to get media url: {resp.text}")
                return None
            
            media_url = resp.json().get("url")
            if not media_url:
                return None
                
            # 2. Download actual bytes with the SAME auth header (CDN Trap)
            download_resp = requests.get(media_url, headers=headers, timeout=10)
            if download_resp.status_code == 200:
                return download_resp.content
            else:
                print(f"[Meta Download Error] Status {download_resp.status_code}")
                return None
                
        except Exception as e:
            print(f"[Meta Download Exception] {e}")
            return None
"""

content = content.replace('# Singleton instance', new_methods + '\n# Singleton instance')

with open('app/services/meta_whatsapp_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("meta_whatsapp_service.py updated.")
