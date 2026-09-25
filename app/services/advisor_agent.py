import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class MerchantActionableInsight(BaseModel):
    headline: str = Field(description="Maksimum 6 kelimelik çarpıcı teşhis başlığı")
    primary_bottleneck: str = Field(description="En büyük kayıp nedeni (örn: Fiyat Direnci, Kargo Ücreti)")
    suggested_action: str = Field(description="Mağaza sahibinin panelden veya siteden hemen uygulayabileceği 1-2 cümlelik net taktik")
    projected_recovery_lift: str = Field(description="Bu aksiyon alınırsa kurtarılabilecek tahmini sepet veya ciro artışı (örn: +14 Sepet / ₺18.500)")
    urgency_level: str = Field(description="LOW, MEDIUM, HIGH, CRITICAL")

class AntigravityDashboardAdvisor:
    def __init__(self):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            self.client = genai.Client(api_key=gemini_api_key)
        else:
            self.client = genai.Client()
        self.model_id = "gemini-3.6-flash"

    async def generate_merchant_insight(
        self,
        kpis: Dict[str, Any],
        lost_sales: List[Dict[str, Any]],
        cross_sell_performance: List[Dict[str, Any]]
    ) -> MerchantActionableInsight:
        """
        Mağaza metriklerini analiz ederek panoda gösterilecek 
        eyleme geçirilebilir içgörüyü deterministik JSON olarak üretir.
        """
        system_instruction = (
            "Sen CartNudge e-ticaret terk edilen sepet panosunun baş CRO (Dönüşüm Oranı Optimizasyonu) stratejistisin. "
            "Görevin, mağazanın metriklerini, kayıp satış otopsisini ve cross-sell başarısını inceleyerek "
            "mağaza sahibine panoda gösterilecek somut, doğrudan uygulanabilir ve sayısal veriye dayalı bir eylem planı sunmaktır. "
            "Genel geçer veya belirsiz konuşma; daima net sayılar, yüzdeler ve oranlar üzerinden git."
        )

        user_prompt = f"""
[GÜNCEL MAĞAZA METRİKLERİ]:
- Terk Edilen Toplam Sepet: {kpis.get('total_abandoned', 0)}
- Kurtarma Oranı: %{kpis.get('recovery_rate', 0.0)}
- Kurtarılan Net Ciro: ₺{kpis.get('recovered_revenue', 0.0)}
- Tamamlayıcı Ürün (Cross-Sell) Cirosu: ₺{kpis.get('cross_sell_revenue', 0.0)}
- Sesli Mesajla Kurtarılan: {kpis.get('voice_recovered_count', 0)} sepet

[KAYIP SATIŞ DAĞILIMI (LOST SALES RADAR)]:
{lost_sales}

[ÇAPRAZ SATIŞ DÖNÜŞÜMÜ]:
{cross_sell_performance}

Bu verileri adli tıp titizliğiyle değerlendir ve mağaza sahibine panoda göstereceğimiz stratejik tavsiyeyi yapılandırılmış formatta oluştur:
"""

        response = await self.client.aio.models.generate_content(
            model=self.model_id,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=MerchantActionableInsight
            )
        )

        return MerchantActionableInsight.model_validate_json(response.text)

advisor_agent = AntigravityDashboardAdvisor()
