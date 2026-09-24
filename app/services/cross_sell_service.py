import httpx
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ShopifyCrossSellAgent:
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain.replace("https://", "").rstrip("/")
        self.access_token = access_token
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    async def get_smart_cross_sell(
        self,
        cart_items: List[Dict[str, Any]],
        discount_code: str = "NUDGE15",
        max_ratio: float = 0.25
    ) -> Dict[str, Any]:
        """
        Sepetteki ana ürüne göre tamamlayıcı (complementary) ürün bulur.
        Stok kontrolü ve fiyat tavanı (%25 kuralı) filtrelemesi yapar.
        Tekil permalink üretir.
        """
        if not cart_items:
            return {"has_upsell": False, "checkout_url": None, "offered_variant_id": None}

        # 1. Sepet toplamını ve en yüksek fiyatlı ana ürünü tespit et
        cart_total = sum(float(item.get("price", 0)) * int(item.get("quantity", 1)) for item in cart_items)
        primary_item = max(cart_items, key=lambda x: float(x.get("price", 0)))
        primary_product_id = primary_item.get("product_id")
        
        # Test datası (mock data) için fallback
        if not primary_product_id:
            primary_product_id = "mock_product_id"
            
        # Dürtüsel satın alma için tavan fiyat eşiği (Sepetin maksimum %25'i)
        max_upsell_price = cart_total * max_ratio

        # 2. Shopify Complementary Recommendations API Çağrısı
        recommendations_url = (
            f"https://{self.shop_domain}/recommendations/products.json"
            f"?product_id={primary_product_id}&intent=complementary&limit=5"
        )

        selected_upsell = None

        if self.access_token and self.access_token != "mock_token":
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    response = await client.get(recommendations_url, headers=self.headers)
                    if response.status_code == 200:
                        recommended_products = response.json().get("products", [])
                        
                        # 3. Stok ve Fiyat Tavanı Filtresi
                        for product in recommended_products:
                            variants = product.get("variants", [])
                            for variant in variants:
                                price = float(variant.get("price", 0))
                                available = variant.get("available", True)
                                
                                # Ürün stokta mı ve fiyatı tavan sınırın altında mı?
                                if available and price <= max_upsell_price:
                                    selected_upsell = {
                                        "product_id": product.get("id"),
                                        "variant_id": variant.get("id"),
                                        "title": product.get("title"),
                                        "variant_title": variant.get("title"),
                                        "price": price
                                    }
                                    break
                            if selected_upsell:
                                break
                except Exception as e:
                    logger.error(f"Cross-sell API Error: {e}")
                    selected_upsell = None
        else:
            # EĞER MOCK SEED İLE ÇALIŞIYORSAK TEST İÇİN MOCK CROSS-SELL ÜRETELİM
            # This is critical so the AI gets the prompt during local tests before live Shopify connects.
            selected_upsell = {
                "product_id": "999888",
                "variant_id": "999888_var",
                "title": "Deri Bakım Kremi",
                "variant_title": "Standart Boy",
                "price": round(cart_total * 0.15, 2)  # Fits the 25% max ratio constraint
            }

        # 4. Çoklu Varyant Permalink İnşası
        # Format: /cart/{variant_id}:{qty},{variant_id}:{qty}?discount={code}
        cart_segments = []
        for item in cart_items:
            vid = item.get('variant_id')
            if not vid:
                vid = "123456" # fallback for mock
            qty = item.get('quantity', 1)
            cart_segments.append(f"{vid}:{qty}")

        if selected_upsell:
            # Önerilen ürünü sepet linkine 1 adet ekle
            cart_segments.append(f"{selected_upsell['variant_id']}:1")
            checkout_url = f"https://{self.shop_domain}/cart/{','.join(cart_segments)}?discount={discount_code}"
            
            return {
                "has_upsell": True,
                "upsell_product": selected_upsell["title"],
                "upsell_price": selected_upsell["price"],
                "offered_variant_id": selected_upsell["variant_id"],
                "checkout_url": checkout_url,
                "prompt_context": (
                    f"Müşteriye indirimini ver. Yanında sepetindeki {primary_item.get('title', 'ürün')} "
                    f"ile kusursuz uyum sağlayan '{selected_upsell['title']}' ({selected_upsell['price']}) "
                    f"ürününü tek cümleyle tavsiye et. İki ayrı link verme; her ikisinin de sepete ekli "
                    f"ve indirimin uygulanmış olduğu şu tek linki paylaş: {checkout_url}"
                )
            }

        # Uygun tamamlayıcı ürün bulunamazsa sadece mevcut sepeti indirimle döndür
        checkout_url = f"https://{self.shop_domain}/cart/{','.join(cart_segments)}?discount={discount_code}"
        return {
            "has_upsell": False,
            "offered_variant_id": None,
            "checkout_url": checkout_url,
            "prompt_context": (
                f"Müşteriye indirimini ver ve sepetini tamamlaması için şu tek tıkla "
                f"ödeme linkini paylaş: {checkout_url}"
            )
        }
