import re

with open('app/services/meta_whatsapp_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('import requests', 'import requests\nimport httpx')
content = content.replace('requests.post(url, headers=headers, json=payload, timeout=5)', 'async with httpx.AsyncClient() as client:\n            await client.post(url, headers=headers, json=payload, timeout=5.0)')

old_download = """        try:
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
            return None"""

new_download = """        try:
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
            return None"""

content = content.replace(old_download, new_download)

with open('app/services/meta_whatsapp_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated meta_whatsapp_service to use httpx.")
