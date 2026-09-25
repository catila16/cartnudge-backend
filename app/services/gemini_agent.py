from app.services.persona_manager import GeminiPersonaDirector
import os
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 1. Kayıp Satış Raporlama Aracı
report_lost_sale_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="report_lost_sale",
            description=(
                "Müşteri teklifi kesin olarak reddettiğinde, bütçesinin yetmediğini söylediğinde "
                "veya vazgeçtiğinde çağrılır. Müşteri pazarlık yapıyorsa (örn: 'Daha fazla indirim var mı?') ASLA çağrılmaz."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "category": types.Schema(
                        type=types.Type.STRING,
                        enum=[
                            "PRICE_TOO_HIGH",
                            "SHIPPING_COST",
                            "SHIPPING_TIME",
                            "COMPETITOR",
                            "POSTPONED",
                            "NOT_INTERESTED",
                            "OTHER"
                        ],
                        description="Satış kaybının ana teknik gerekçesi."
                    ),
                    "detail": types.Schema(
                        type=types.Type.STRING,
                        description="Müşterinin vazgeçme gerekçesinin 1-2 cümlelik net özeti."
                    ),
                    "farewell_message": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Müşterinin konuştuğu dilde hazırlanmış; son derece kibar, "
                            "anlayışlı ve gelecekteki olası alışverişe açık kapı bırakan veda mesajı."
                        )
                    )
                },
                required=["category", "detail", "farewell_message"]
            )
        )
    ]
)

class CartNudgeGeminiAgent:
    def __init__(self):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        # Fallback to OPENAI_API_KEY for seamless transition or just require GEMINI_API_KEY
        # If it's missing, genai.Client might pick it from env or fail. We'll pass it explicitly if available.
        if gemini_api_key:
            self.client = genai.Client(api_key=gemini_api_key)
        else:
            # Let SDK attempt to find it or fail gracefully later
            self.client = genai.Client()
        self.model_id = "gemini-3.6-flash"

    def build_system_instruction(
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
        )

    async def execute_turn(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]],
        system_instruction: str
    ) -> Dict[str, Any]:
        """
        Gemini ile tek turda çıkarım yapar; tool çağrısı varsa yakalar, yoksa düz metin döner.
        """
        try:
            # Konuşma geçmişini Gemini formatına çevir
            contents = []
            for msg in chat_history:
                if not isinstance(msg, dict): continue
                role = "user" if msg.get("role") == "user" else "model"
                content_val = msg.get("content", "")
                if not content_val: continue
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content_val)]))
            
            # Son kullanıcı mesajını ekle
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[report_lost_sale_tool],
                temperature=0.3
            )

            # Await the async client call
            response = await self.client.aio.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=config
            )

            # Tool Call Denetimi (Kayıp Satış Tetiklendi mi?)
            if response.function_calls:
                for call in response.function_calls:
                    if call.name == "report_lost_sale":
                        args = call.args
                        return {
                            "type": "LOST_SALE",
                            "category": args.get("category"),
                            "detail": args.get("detail"),
                            "farewell_message": args.get("farewell_message")
                        }

            # Standart Müzakere / Satış Kapatma Yanıtı
            return {
                "type": "MESSAGE",
                "reply_text": response.text.strip() if response.text else "Anlayışınız için teşekkür ederiz."
            }
        except Exception as e:
            logger.error(f"Gemini execute_turn error: {e}")
            return {
                "type": "MESSAGE",
                "reply_text": "Şu anda işleminizi gerçekleştiremiyorum. Lütfen daha sonra tekrar deneyin."
            }

gemini_agent = CartNudgeGeminiAgent()
