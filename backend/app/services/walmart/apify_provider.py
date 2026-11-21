"""
Apify Walmart Data Provider Adapter (Phase 3).
Provides an integration adapter for Apify actors configured for Walmart product data.
Credentials remain strictly on the backend.
"""
import os
import urllib.parse
import urllib.request
import json
from typing import List, Dict, Any, Optional, Tuple
from app.services.walmart.base import WalmartProviderBase, WalmartProduct, WalmartSellerInfo
from app.services.walmart.normalizer import normalize_walmart_product
from app.services.walmart.seller_service import parse_walmart_seller_url


class ApifyWalmartProvider(WalmartProviderBase):
    """
    Adapter for Apify Walmart scraping actors.
    Supports token configuration and explicit capability reporting.
    """

    def __init__(self, api_token: Optional[str] = None, actor_id: Optional[str] = None):
        self.api_token = api_token or os.getenv("APIFY_TOKEN", "")
        self.actor_id = actor_id or os.getenv("APIFY_WALMART_ACTOR_ID", "compass/walmart-scraper")
        self.base_url = f"https://api.apify.com/v2/acts/{self.actor_id}/run-sync-get-dataset-items"
        self.provider_name = "apify_walmart"

    def get_provider_name(self) -> str:
        return self.provider_name

    def identify_seller(self, url_or_id: str) -> Optional[WalmartSellerInfo]:
        parsed = parse_walmart_seller_url(url_or_id)
        if not parsed["valid"]:
            return None
        seller_id = parsed["seller_id"]
        return WalmartSellerInfo(
            seller_id=seller_id,
            seller_name=parsed.get("seller_name") or f"Walmart Seller {seller_id}",
            storefront_url=parsed["storefront_url"],
            product_count=None,
            rating=None,
            is_verified=True,
            provider=self.provider_name,
            is_demo=False,
        )

    def get_seller_products(
        self,
        seller_id: str,
        limit: int = 50,
        page: int = 1,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> Tuple[List[WalmartProduct], Optional[int]]:
        if not self.api_token:
            raise RuntimeError("APIFY_TOKEN is not configured in backend environment.")

        start_urls = [{"url": f"https://www.walmart.com/seller/{seller_id}"}]
        payload = {
            "startUrls": start_urls,
            "maxItems": limit,
        }
        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}?token={self.api_token}"

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "CommerceQuarry-Agent/1.0"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            items = json.loads(resp.read().decode("utf-8"))

        normalized = [
            normalize_walmart_product(
                item,
                provider_name=self.provider_name,
                seller_id=seller_id,
                is_demo=False,
            )
            for item in items[:limit]
        ]
        return normalized, len(normalized)

    def get_capabilities(self) -> Dict[str, Any]:
        configured = bool(self.api_token)
        return {
            "seller_identification": True,
            "seller_products": True,
            "pagination": True,
            "price_filtering": False,
            "category_filtering": False,
            "is_live": True,
            "requires_credentials": True,
            "configured": configured,
            "rate_limit_rps": 2,
            "description": "Apify cloud actor adapter for authorized Walmart dataset runs.",
        }
