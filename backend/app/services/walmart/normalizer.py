"""
Walmart Product Normalizer (Phase 4).
Safely transforms raw provider payloads into standardized WalmartProduct instances.
Missing values are preserved as None without hallucination.
"""
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.walmart.base import WalmartProduct


def normalize_walmart_product(
    raw: Dict[str, Any],
    provider_name: str = "unknown",
    seller_id: Optional[str] = None,
    seller_name: Optional[str] = None,
    is_demo: bool = False,
) -> WalmartProduct:
    """Normalize raw product dictionary into a validated WalmartProduct instance."""
    product_id = str(
        raw.get("walmart_product_id")
        or raw.get("product_id")
        or raw.get("us_item_id")
        or raw.get("item_id")
        or raw.get("id")
        or ""
    ).strip()

    title = str(raw.get("product_title") or raw.get("title") or raw.get("name") or "").strip()

    price = 0.0
    raw_price = raw.get("current_price") or raw.get("price") or raw.get("primary_offer", {}).get("offer_price")
    if raw_price is not None:
        try:
            if isinstance(raw_price, (int, float)):
                price = float(raw_price)
            else:
                cleaned = str(raw_price).replace("$", "").replace(",", "").strip()
                price = float(cleaned)
        except (ValueError, TypeError):
            price = 0.0

    orig_price = None
    raw_orig = raw.get("original_price") or raw.get("was_price")
    if raw_orig is not None:
        try:
            cleaned = str(raw_orig).replace("$", "").replace(",", "").strip()
            orig_price = float(cleaned)
        except (ValueError, TypeError):
            orig_price = None

    url = str(
        raw.get("product_url")
        or raw.get("url")
        or (f"https://www.walmart.com/ip/{product_id}" if product_id else "")
    )

    weight_lbs = None
    raw_weight = raw.get("weight_lbs") or raw.get("weight")
    if raw_weight is not None:
        try:
            weight_lbs = float(raw_weight)
        except (ValueError, TypeError):
            weight_lbs = None

    pkg_qty = 1
    raw_qty = raw.get("package_quantity") or raw.get("pack_count") or raw.get("quantity")
    if raw_qty is not None:
        try:
            pkg_qty = max(1, int(raw_qty))
        except (ValueError, TypeError):
            pkg_qty = 1

    return WalmartProduct(
        product_title=title,
        walmart_product_id=product_id,
        product_url=url,
        image_url=raw.get("image_url") or raw.get("thumbnail") or raw.get("image"),
        current_price=price,
        original_price=orig_price,
        currency=raw.get("currency", "USD"),
        brand=raw.get("brand"),
        upc=str(raw["upc"]).strip() if raw.get("upc") else None,
        gtin=str(raw["gtin"]).strip() if raw.get("gtin") else None,
        model_number=str(raw["model_number"]).strip() if raw.get("model_number") else (str(raw["model"]).strip() if raw.get("model") else None),
        mpn=str(raw["mpn"]).strip() if raw.get("mpn") else None,
        description=raw.get("description"),
        specifications=raw.get("specifications") or {},
        dimensions=raw.get("dimensions"),
        weight_lbs=weight_lbs,
        package_quantity=pkg_qty,
        category=raw.get("category"),
        availability=raw.get("availability", "in_stock"),
        seller_id=seller_id or raw.get("seller_id"),
        seller_name=seller_name or raw.get("seller_name"),
        provider_name=provider_name,
        collected_at=datetime.utcnow().isoformat(),
        data_freshness=datetime.utcnow().isoformat(),
        is_demo=is_demo,
        raw_data=raw if not is_demo else None,
    )
