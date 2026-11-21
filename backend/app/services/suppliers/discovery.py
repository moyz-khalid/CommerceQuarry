"""
Supplier Discovery Service (Phase 5).

Finds candidate listings for an Amazon product across supported supplier marketplaces:
  - Home Depot
  - Walmart
  - Lowe's
  - AliExpress

Normalizes supplier listings into internal schema before matching.
"""
from typing import List, Dict, Any, Optional

SUPPORTED_SUPPLIERS = ["home_depot", "walmart", "lowes", "aliexpress"]


def normalize_supplier_product(raw: Dict[str, Any], default_supplier: str = "Unknown") -> Dict[str, Any]:
    """Normalize supplier candidate listing into standard format."""
    supplier_name = raw.get("supplier_name") or default_supplier
    return {
        "supplier_name": supplier_name,
        "supplier_title": str(raw.get("supplier_title") or raw.get("title") or ""),
        "supplier_price": float(raw.get("supplier_price") or raw.get("price") or 0.0),
        "supplier_url": str(raw.get("supplier_url") or raw.get("url") or ""),
        "brand": str(raw.get("brand") or ""),
        "upc": str(raw.get("upc") or "").strip(),
        "mpn": str(raw.get("mpn") or raw.get("model") or "").strip(),
        "model": str(raw.get("model") or raw.get("mpn") or "").strip(),
        "condition": str(raw.get("condition") or "new").lower(),
        "package_quantity": int(raw.get("package_quantity") or 1),
        "in_stock": bool(raw.get("in_stock", True)),
    }


def search_supplier_candidates(
    amazon_product: Dict[str, Any],
    selected_suppliers: Optional[List[str]] = None,
    demo: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search candidate supplier listings for an Amazon product across selected suppliers.
    Returns normalized candidate records.
    """
    if demo:
        from app.services.sourcing.demo_provider import demo_find_supplier_candidates
        raw_candidates = demo_find_supplier_candidates(amazon_product, selected_suppliers)
        return [normalize_supplier_product(c) for c in raw_candidates]

    # Live multi-supplier sequence (Phase 11)
    from app.services.suppliers.multi_search import execute_multi_supplier_search
    return execute_multi_supplier_search(amazon_product, selected_suppliers)
