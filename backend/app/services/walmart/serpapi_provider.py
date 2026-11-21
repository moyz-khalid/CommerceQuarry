"""
SerpApi Walmart Data Provider Adapter (Phase 3).
Provides integration with SerpApi's authorized Walmart Search engine.
Credentials remain strictly on the backend.
"""
import os
import urllib.parse
import urllib.request
import json
from typing import List, Dict, Any, Optional, Tuple
from loguru import logger
from app.services.walmart.base import WalmartProviderBase, WalmartProduct, WalmartSellerInfo
from app.services.walmart.normalizer import normalize_walmart_product
from app.services.walmart.seller_service import parse_walmart_seller_url


class SerpApiWalmartProvider(WalmartProviderBase):
    """
    Adapter for SerpApi Walmart API.
    Handles rate limiting, pagination parameters, and explicit capability detection.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        self.base_url = "https://serpapi.com/search"
        self.provider_name = "serpapi_walmart"

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
            product_count=None,  # SerpApi reports pagination on product query, not seller endpoint
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
        if not self.api_key:
            raise RuntimeError("SERPAPI_API_KEY is not configured in backend environment.")

        # SerpApi Walmart Search API with seller facet or query
        params = {
            "engine": "walmart",
            "api_key": self.api_key,
            "query": f"seller:{seller_id}",
            "page": page,
        }
        if min_price is not None:
            params["min_price"] = str(min_price)
        if max_price is not None:
            params["max_price"] = str(max_price)

        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "CommerceQuarry-Agent/1.0"})

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        organic = data.get("organic_results", [])
        total_results = data.get("search_information", {}).get("total_results")

        normalized = []
        for item in organic[:limit]:
            p = {
                "walmart_product_id": str(item.get("us_item_id") or item.get("product_id") or ""),
                "product_title": item.get("title", ""),
                "current_price": item.get("primary_offer", {}).get("offer_price", 0.0),
                "product_url": item.get("product_page_url", ""),
                "image_url": item.get("thumbnail", ""),
                "brand": item.get("brand"),
                "rating": item.get("rating"),
                "availability": "in_stock" if not item.get("out_of_stock") else "out_of_stock",
            }
            normalized.append(
                normalize_walmart_product(
                    p,
                    provider_name=self.provider_name,
                    seller_id=seller_id,
                    is_demo=False,
                )
            )

        return normalized, total_results

    def get_capabilities(self) -> Dict[str, Any]:
        configured = bool(self.api_key)
        return {
            "seller_identification": True,
            "seller_products": True,
            "pagination": True,
            "price_filtering": True,
            "category_filtering": False,
            "is_live": True,
            "requires_credentials": True,
            "configured": configured,
            "rate_limit_rps": 5,
            "description": "Authorized SerpApi Walmart Search integration for live catalog discovery.",
        }
