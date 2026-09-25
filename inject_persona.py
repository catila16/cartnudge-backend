import re

with open('app/services/gemini_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

imports = "from app.services.persona_manager import GeminiPersonaDirector\n"
if "GeminiPersonaDirector" not in content:
    content = imports + content

old_build = """    def build_system_instruction(
        self,
        shop_domain: str,
        cart_summary: str,
        discount_ceiling: str,
        cross_sell_context: Optional[str],
        customer_language: str
    ) -> str:
        return f\"\"\"
Sen {shop_domain} mağazasının WhatsApp üzerindeki uzman, ikna kabiliyeti yüksek satış temsilcisisin.

HEDEF: Müşterinin itirazlarını çözmek, sepetini tamamlamasını sağlamak ve kâr marjını korumak.

BAĞLAM:
- Müşterinin Terk Ettiği Sepet: {cart_summary}
- Tanımlanabilir Maksimum İndirim Tavanı: {discount_ceiling}
- Müşteri Dili / Tercihi: {customer_language}

KAT'İ KURALLAR (KORUYUCU KORKULUKLAR):
1. DİL: Müşteri hangi dilde yazıyorsa veya ses kaydı attıysa YALNIZCA o dilde yanıt ver.
2. İNDİRİM SINIRI: Belirlenen {discount_ceiling} indirim tavanının 1 kuruş üzerine ASLA çıkma.
3. BEDAVA ÜRÜN YOK: Çapraz satışta önerilen yan ürünler asla hediye veya ücretsiz değildir. Yalnızca indirim kodunun tüm sepete uygulanacağını belirt.
4. TEK TIKLA SATIN ALMA: Satın alma linki verirken müşteriyi asla mağazada arayışa sokma; doğrudan verilen checkout linkini ilet.
5. KAYIP SATIŞ PROSEDÜRÜ: Müşteri indirime rağmen net bir dille almayacağını, bütçesinin yetersiz olduğunu veya vazgeçtiğini söylerse müzakereyi uzatma. DERHAL 'report_lost_sale' aracını çağır ve aracın içine müşterinin dilinde zarif bir veda mesajı ekle.

{cross_sell_context if cross_sell_context else ''}
\"\"\""""

new_build = """    def build_system_instruction(
        self,
        shop_domain: str,
        cart_summary: str,
        discount_ceiling: str,
        cross_sell_context: Optional[str],
        customer_language: str
    ) -> str:
        return GeminiPersonaDirector.construct_instruction(
            shop_domain=shop_domain,
            cart_summary=cart_summary,
            discount_ceiling=discount_ceiling,
            persona_key="friendly",
            customer_language=customer_language,
            cross_sell_context=cross_sell_context
        )"""

content = content.replace(old_build, new_build)

with open('app/services/gemini_agent.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("gemini_agent.py updated to use Persona Manager.")
