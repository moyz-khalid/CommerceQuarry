"""
CSV & Manual Walmart Product Provider (Phase 3 & Phase 4).
Allows importing seller product catalogs from CSV files or structured manual entries.
"""
import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from app.services.walmart.base import WalmartProviderBase, WalmartProduct, WalmartSellerInfo
from app.services.walmart.normalizer import normalize_walmart_product


class CsvWalmartProvider(WalmartProviderBase):
    """
    Provider that consumes user-uploaded CSV catalogs or manual lists.
    Guarantees full transparency of source data without scraping.
    """

    def __init__(self, raw_products: Optional[List[Dict[str, Any]]] = None, seller_id: str = "manual_import"):
        self.provider_name = "csv_import"
        self.seller_id = seller_id
        self._products = raw_products or []

    def get_provider_name(self) -> str:
        return self.provider_name

    def identify_seller(self, url_or_id: str) -> Optional[WalmartSellerInfo]:
        return WalmartSellerInfo(
            seller_id=self.seller_id,
            seller_name="Custom CSV / Manual Catalog",
            storefront_url="local://catalog.csv",
            product_count=len(self._products),
            rating=5.0,
            is_verified=True,
            provider=self.provider_name,
            is_demo=False,
        )

    @classmethod
    def from_csv_text(cls, csv_text: str, seller_id: str = "csv_upload") -> "CsvWalmartProvider":
        """Parse raw CSV text into a structured product list."""
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        products = []
        for row in reader:
            # Map common CSV header variants
            p_id = (
                row.get("walmart_product_id")
                or row.get("product_id")
                or row.get("item_id")
                or row.get("id")
                or row.get("sku")
                or ""
            )
            title = row.get("product_title") or row.get("title") or row.get("name") or ""
            price_str = row.get("current_price") or row.get("price") or row.get("walmart_price") or "0"
            try:
                price = float(price_str.replace("$", "").replace(",", "").strip())
            except ValueError:
                price = 0.0

            products.append({
                "walmart_product_id": p_id,
                "product_title": title,
                "current_price": price,
                "brand": row.get("brand"),
                "upc": row.get("upc"),
                "model_number": row.get("model_number") or row.get("model"),
                "mpn": row.get("mpn"),
                "category": row.get("category"),
                "product_url": row.get("product_url") or row.get("url") or f"https://www.walmart.com/ip/{p_id}",
                "image_url": row.get("image_url") or row.get("image"),
                "package_quantity": int(row.get("package_quantity") or 1),
            })
        return cls(raw_products=products, seller_id=seller_id)

    def get_seller_products(
        self,
        seller_id: str,
        limit: int = 50,
        page: int = 1,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> Tuple[List[WalmartProduct], Optional[int]]:
        filtered = []
        for raw in self._products:
            price = float(raw.get("current_price", 0))
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            if category and raw.get("category", "").lower() != category.lower():
                continue
            filtered.append(raw)

        total_count = len(filtered)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paged_items = filtered[start_idx:end_idx]

        products = [
            normalize_walmart_product(
                raw=item,
                provider_name=self.provider_name,
                seller_id=self.seller_id,
                seller_name="Custom CSV Catalog",
                is_demo=False,
            )
            for item in paged_items
        ]
        return products, total_count

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "seller_identification": True,
            "seller_products": True,
            "pagination": True,
            "price_filtering": True,
            "category_filtering": True,
            "is_live": True,
            "requires_credentials": False,
            "rate_limit_rps": 1000,
            "configured": True,
            "description": "User-supplied CSV catalog import. Accurate, user-controlled data.",
        }
