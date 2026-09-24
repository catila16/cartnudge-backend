import re

with open('app/services/openai_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add parameter to signature if not present
if 'cross_sell_instruction' not in content:
    content = re.sub(
        r'latest_message: str\s*\)\s*->\s*str:',
        'latest_message: str,\n        cross_sell_instruction: str = ""\n    ) -> str:',
        content
    )

    # Append to system prompt
    pattern = r'(\{checkout_url\}[^"]*""")'
    replacement = r'\1\n\n        if cross_sell_instruction:\n            system_prompt += f"\\n\\n[GÜNCEL SATIŞ TALİMATI]: {cross_sell_instruction}"\n            system_prompt += "\\n\\nDİKKAT: Önerilen ek ürün (yan ürün) KESİNLİKLE hediye veya bedava değildir. Özel bir ekstra indirim yapılamaz. Yalnızca mevcut indirim kodunun tüm sepet toplamına uygulanacağını belirterek teklif et."'
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open('app/services/openai_service.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated openai_service.py')
else:
    print('Already updated.')
