"""
Demo Amazon Provider Adapter (Phase 10).
Wraps the simulated demo provider into the standard AmazonProviderBase interface.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.services.amazon.base import AmazonProviderBase, AmazonProduct, AMAZON_URL_PATTERN
from app.services.sourcing.demo_provider import (
    demo_category_products,
    demo_product_by_asin,
    demo_seller_products,
)


class DemoAmazonProvider(AmazonProviderBase):
    """Simulated provider that yields deterministic Amazon products for testing and demo workflows."""

    def __init__(self):
        self.provider_name = "demo"

    def _dict_to_product(self, d: Dict[str, Any]) -> AmazonProduct:
        return AmazonProduct(
            asin=d.get("asin", ""),
            title=d.get("title", ""),
            brand=d.get("brand"),
            price=float(d.get("price") or d.get("amazon_price", 0.0)),
            url=d.get("url") or f"https://www.amazon.com/dp/{d.get('asin')}",
            image_url=d.get("image_url") or d.get("image"),
            upc=d.get("upc"),
            mpn=d.get("mpn"),
            model_number=d.get("model_number") or d.get("model"),
            weight_lbs=float(d.get("weight_lbs")) if d.get("weight_lbs") else 1.0,
            dimensions=d.get("dimensions"),
            category=d.get("category"),
            in_stock=bool(d.get("in_stock", True)),
            rating=float(d.get("rating", 4.5)),
            review_count=int(d.get("review_count", 150)),
            source="demo_simulation",
            retrieved_at=datetime.utcnow().isoformat(),
            raw_data=d,
        )

    def lookup_asin(self, asin: str) -> Optional[AmazonProduct]:
        items = demo_product_by_asin(asin)
        if items:
            return self._dict_to_product(items[0])
        return None

    def lookup_url(self, url: str) -> Optional[AmazonProduct]:
        m = AMAZON_URL_PATTERN.search(url)
        if m:
            asin = m.group(1) or m.group(2)
            return self.lookup_asin(asin)
        return None

    def discover_category(
        self,
        category: str,
        max_products: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[AmazonProduct]:
        items = demo_category_products(category, max_products)
        return [self._dict_to_product(i) for i in items]

    def get_seller_inventory(
        self,
        seller_id: str,
        max_products: int = 10,
    ) -> List[AmazonProduct]:
        items = demo_seller_products(seller_id)[:max_products]
        return [self._dict_to_product(i) for i in items]

    def check_capabilities(self) -> Dict[str, bool]:
        return {
            "lookup_asin": True,
            "lookup_url": True,
            "category_discovery": True,
            "seller_inventory": True,
            "real_time_pricing": True,
            "images": True,
        }

    def test_connection(self) -> Dict[str, Any]:
        return {
            "connected": True,
            "status": "ready",
            "provider": "demo",
            "message": "Demo mode provider is operational with 0 external credentials needed.",
        }
