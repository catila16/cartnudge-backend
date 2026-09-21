import os
import json

class OpenAIService:
    @staticmethod
    def process_negotiation_reply(
        customer_name: str,
        cart_items: list,
        cart_url: str,
        discount_percentage: int,
        tone: str,
        chat_history: list,
        latest_message: str
    ) -> str:
        """
        Geliştirme/Test aşaması için akıllı Mock Yapay Zeka motoru.
        Gelen mesajdaki anahtar kelimelere göre dinamik pazarlık yapar.
        """
        msg = (latest_message or "").lower()
        name = customer_name or "Değerli Müşterimiz"

        # 1. İndirim / Fiyat Pazarlığı Senaryosu
        if any(w in msg for w in ["indirim", "fiyat", "pahalı", "kupon", "ucuz", "bütçe", "discount"]):
            if discount_percentage > 0:
                return (
                    f"Merhaba {name}! Sepetindeki ürünleri kaçırmanı istemem. "
                    f"Sana özel anında %{discount_percentage} indirim tanımladım! 🎁 "
                    f"İndirimli linkin: {cart_url}?discount=NUDGE{discount_percentage}"
                )
            else:
                return f"Merhaba {name}, fiyatlarımız şu an en avantajlı seviyede! Ürünlerin tükenmeden sepetini tamamlayabilirsin: {cart_url}"

        # 2. Kargo Sorusu Senaryosu
        elif any(w in msg for w in ["kargo", "teslimat", "shipping", "ulaşır"]):
            return f"Siparişlerin 24 saat içinde özenle kargoya verilir {name}. Alışverişini tamamlamak için tıkla: {cart_url}"

        # 3. Genel Yanıt / Samimi Hatırlatma
        else:
            return (
                f"Harika bir tercih {name}! Sepetindeki ürünler tükenmeden alışverişini "
                f"tamamlamak istersen linkin burada: {cart_url}\nBaşka bir sorun varsa buradayım!"
            )

    @staticmethod
    def generate_cart_recovery_message(line_items: list) -> str:
        """Legacy MVP method for initial outbound if needed."""
        return "Merhaba! CartNudge mağazasında sepetinizde harika ürünler bıraktığınızı fark ettik. Siparişinizi tamamlamak için yardıma ihtiyacınız var mı? Size özel ufak bir sürprizimiz olabilir! 🎁"

openai_service = OpenAIService()
