"""
Multi-Supplier Search Sequence & Candidate Ranker (Phase 11, Section 11.2).

Executes the strict 8-step supplier search sequence for each Amazon product:
  1. Search by UPC/EAN/GTIN
  2. Search by manufacturer part number (MPN)
  3. Search by model number
  4. Search by brand + product name
  5. Search by normalized title
  6. Normalize and deduplicate candidates across suppliers
  7. Rank candidates
  8. Return eligible candidate pool
"""
import re
from typing import List, Dict, Any, Optional
from app.services.suppliers.base import SupplierCandidate, SupplierAdapterBase
from app.services.suppliers.homedepot_adapter import HomeDepotAdapter
from app.services.suppliers.walmart_adapter import WalmartAdapter
from app.services.suppliers.lowes_adapter import LowesAdapter
from app.services.suppliers.aliexpress_adapter import AliExpressAdapter

# Registry of supported supplier adapters
ADAPTER_MAP: Dict[str, type] = {
    "home_depot": HomeDepotAdapter,
    "walmart": WalmartAdapter,
    "lowes": LowesAdapter,
    "aliexpress": AliExpressAdapter,
}


def clean_title(title: str) -> str:
    """Normalize product title removing extraneous noise."""
    t = re.sub(r"\[.*?\]|\(.*?\)", "", title)
    t = re.sub(r"[^a-zA-Z0-9\s]", " ", t)
    return " ".join(t.split()[:8])


def execute_multi_supplier_search(
    amazon_product: Dict[str, Any],
    selected_suppliers: Optional[List[str]] = None,
    adapters: Optional[Dict[str, SupplierAdapterBase]] = None,
) -> List[Dict[str, Any]]:
    """
    Executes the 8-stage search sequence across selected suppliers.
    Returns normalized and ranked candidate dicts.
    """
    suppliers_to_query = selected_suppliers or ["home_depot", "walmart", "lowes", "aliexpress"]
    active_adapters = adapters or {s: ADAPTER_MAP[s]() for s in suppliers_to_query if s in ADAPTER_MAP}

    upc = str(amazon_product.get("upc") or "").strip() or None
    mpn = str(amazon_product.get("mpn") or "").strip() or None
    model = str(amazon_product.get("model_number") or amazon_product.get("model") or "").strip() or None
    brand = str(amazon_product.get("brand") or "").strip()
    title = str(amazon_product.get("title") or "").strip()
    norm_title = clean_title(title)

    candidates_pool: List[SupplierCandidate] = []

    for name, adapter in active_adapters.items():
        caps = adapter.get_capabilities()

        # Step 1: Search by UPC/EAN if supported and present
        if upc and caps.get("upc_search"):
            c = adapter.search(norm_title, upc=upc, limit=2)
            candidates_pool.extend(c)

        # Step 2: Search by MPN if present
        if mpn and caps.get("mpn_search"):
            c = adapter.search(norm_title, mpn=mpn, limit=2)
            candidates_pool.extend(c)

        # Step 3: Search by model number
        if model and caps.get("model_search") and model != mpn:
            c = adapter.search(norm_title, model=model, limit=2)
            candidates_pool.extend(c)

        # Step 4: Search by brand + product name
        if brand and caps.get("title_search"):
            brand_query = f"{brand} {norm_title}"
            c = adapter.search(brand_query, limit=2)
            candidates_pool.extend(c)

        # Step 5: Search by normalized title
        if caps.get("title_search"):
            c = adapter.search(norm_title, limit=2)
            candidates_pool.extend(c)

    # Step 6: Normalize and deduplicate candidates by (supplier_name, supplier_product_id)
    seen = set()
    deduped: List[SupplierCandidate] = []
    for cand in candidates_pool:
        key = (cand.supplier_name, cand.supplier_product_id)
        if key not in seen:
            seen.add(key)
            deduped.append(cand)

    # Step 7: Rank candidates
    # Priority: exact UPC match (+100), exact MPN match (+50), lower price advantage
    amz_price = float(amazon_product.get("price") or amazon_product.get("amazon_price", 0))

    def _rank_score(cand: SupplierCandidate) -> float:
        score = 0.0
        if upc and cand.upc and upc.lower() == cand.upc.lower():
            score += 100.0
        if mpn and cand.mpn and mpn.lower() == cand.mpn.lower():
            score += 50.0
        # Price advantage bonus (if supplier price is between 30% and 80% of Amazon price)
        if amz_price > 0 and cand.price > 0:
            ratio = cand.price / amz_price
            if 0.2 < ratio < 0.8:
                score += (1.0 - ratio) * 20.0
        return score

    deduped.sort(key=_rank_score, reverse=True)

    # Step 8: Return normalized dictionaries ready for matching
    return [c.to_dict() for c in deduped]
