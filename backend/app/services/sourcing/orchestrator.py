"""
Scan orchestrator — dispatches to the correct sourcing pipeline.

Phase 4: each processed product goes through:
  1. Demo/live provider (fetches Amazon product stub with metadata)
  2. Supplier candidate discovery (multi-supplier candidates from Home Depot, Walmart, Lowe's, AliExpress)
  3. Matching service (UPC / MPN / Title / Pack count / Model conflict verification)
  4. Profitability service (P&L calculation based on supplier cost)
  5. Result persisted to ScanRecord.results
"""
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional

from app.services.sourcing.scan_store import get_scan, update_scan, cancel_scan


def orchestrate_scan(scan_id: UUID) -> None:
    """
    Main pipeline entry point called by the Celery worker (or fallback thread).
    Dispatches based on scan.mode.
    """
    scan = get_scan(scan_id)
    if not scan:
        raise ValueError(f"Scan {scan_id} not found in store.")

    if scan.status == "cancelled":
        return

    mode = scan.mode
    config = scan.config or {}
    demo = scan.demo

    # Mark running
    update_scan(scan_id, status="running")

    try:
        if mode == "category":
            _run_category_scan(scan_id, config, demo)
        elif mode == "seller":
            _run_seller_scan(scan_id, config, demo)
        elif mode == "product":
            _run_product_scan(scan_id, config, demo)
        else:
            raise ValueError(f"Unknown scan mode: {mode}")

        fresh = get_scan(scan_id)
        if fresh and fresh.status == "running":
            update_scan(
                scan_id,
                status="completed",
                completed_at=datetime.utcnow(),
            )
    except Exception as exc:
        update_scan(
            scan_id,
            status="failed",
            error_summary=str(exc),
            completed_at=datetime.utcnow(),
        )
        raise


# ─── Mode handlers ────────────────────────────────────────────────────────────

def _run_category_scan(scan_id: UUID, config: dict, demo: bool) -> None:
    from app.services.amazon import get_amazon_provider
    provider = get_amazon_provider("demo" if demo else None)
    cat = config.get("category", "")
    max_p = config.get("max_products", 100)

    try:
        amazon_products = provider.discover_category(cat, max_p)
        products = [p.to_dict() for p in amazon_products]
    except Exception as exc:
        update_scan(
            scan_id,
            status="failed",
            error_summary=f"Category discovery failed: {str(exc)}",
        )
        return

    _process_products(scan_id, products, demo, config)


def _run_seller_scan(scan_id: UUID, config: dict, demo: bool) -> None:
    seller_id = config.get("seller_id") or ""
    storefront_url = config.get("storefront_url") or ""
    target_id = seller_id or storefront_url

    from app.services.amazon import get_amazon_provider
    provider = get_amazon_provider("demo" if demo else None)

    try:
        amazon_products = provider.get_seller_inventory(target_id)
        products = [p.to_dict() for p in amazon_products]
    except NotImplementedError as nie:
        update_scan(
            scan_id,
            status="failed",
            error_summary=(
                "Seller inventory retrieval is not supported by the currently configured "
                "Amazon provider. Configure a provider that supports this capability."
            ),
        )
        return
    except Exception as exc:
        update_scan(
            scan_id,
            status="failed",
            error_summary=f"Seller inventory retrieval failed: {str(exc)}",
        )
        return

    _process_products(scan_id, products, demo, config)


def _run_product_scan(scan_id: UUID, config: dict, demo: bool) -> None:
    asin = config.get("resolved_asin") or config.get("asin") or ""
    url = config.get("product_url") or ""

    from app.services.amazon import get_amazon_provider
    provider = get_amazon_provider("demo" if demo else None)

    try:
        if asin:
            prod = provider.lookup_asin(asin)
        elif url:
            prod = provider.lookup_url(url)
        else:
            prod = None
        products = [prod.to_dict()] if prod else []
    except Exception as exc:
        update_scan(
            scan_id,
            status="failed",
            error_summary=f"Product lookup failed: {str(exc)}",
        )
        return

    _process_products(scan_id, products, demo, config)


# ─── Shared processing loop ───────────────────────────────────────────────────

def _process_products(
    scan_id: UUID,
    products: List[Dict[str, Any]],
    demo: bool,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """
    For each discovered Amazon product:
      1. Find supplier candidates (Home Depot, Walmart, Lowe's, AliExpress)
      2. Run matching (evaluating identifiers, specifications, pack counts)
      3. Run profitability calculation
      4. Build a ScanResultItem dict and append to scan.results
      5. Update progress counters
    """
    from app.services.matching import match_product_demo, match_product, MatchingEngine
    from app.services.profitability import (
        calculate_profitability_demo,
        calculate_profitability,
        calculate_all_fulfillment_methods,
    )
    from app.services.suppliers.discovery import search_supplier_candidates
    from app.services.ai import should_verify_with_ai, verify_candidate_match

    total = len(products)
    update_scan(scan_id, total=total, progress=0)

    matched_count = 0
    profitable_count = 0
    result_items: List[Dict[str, Any]] = []
    selected_suppliers = (config or {}).get("suppliers", [])

    for i, product in enumerate(products):
        # Respect cancellation on each iteration
        fresh = get_scan(scan_id)
        if not fresh or fresh.status == "cancelled":
            return

        # ── 1. Supplier Candidate Discovery & Stage 3 Ranking ─────────────────
        candidates = search_supplier_candidates(product, selected_suppliers, demo=demo)
        candidate = None
        match_info = None

        if candidates:
            ranked = MatchingEngine.rank_candidates(product, candidates)
            candidate, match_info = ranked[0]
            # If the demo product had an explicit stub flag, let it guide decision
            if demo and "matched" in product and not match_info.get("differences"):
                demo_m = match_product_demo(product)
                match_info["matched"] = demo_m["matched"]
                match_info["final_decision"] = demo_m["final_decision"]
                match_info["manual_review"] = demo_m["manual_review"]
        else:
            match_info = match_product_demo(product)

        # ── 2. Phase 6: DeepSeek AI Verification (Selective) ──────────────────
        if should_verify_with_ai(match_info):
            match_info = verify_candidate_match(product, candidate or {}, match_info)

        # ── 3. Phase 7: Profitability across all fulfillment methods ──────────
        amazon_price = float(product.get("price", 0))
        weight_lbs = product.get("weight_lbs")
        dimensions_str = product.get("dimensions")

        if candidate and "supplier_price" in candidate and float(candidate["supplier_price"]) > 0:
            cost_price = float(candidate["supplier_price"])
            profit_info = calculate_all_fulfillment_methods(
                amazon_price=amazon_price,
                cost_price=cost_price,
                weight_lbs=weight_lbs,
                dimensions_str=dimensions_str,
            )
            profit_info["simulated"] = demo
            if "profitable" in product:
                profit_info["profitable"] = bool(product["profitable"])
        elif demo:
            profit_info = calculate_profitability_demo(product)
        else:
            profit_info = calculate_all_fulfillment_methods(
                amazon_price=amazon_price,
                cost_price=0.0,
                weight_lbs=weight_lbs,
                dimensions_str=dimensions_str,
            )

        # ── Counters ──────────────────────────────────────────────────────────
        if match_info.get("matched"):
            matched_count += 1
        if profit_info.get("profitable"):
            profitable_count += 1

        # ── Build result record ───────────────────────────────────────────────
        result_item = {
            "asin": product.get("asin", ""),
            "title": product.get("title", ""),
            "brand": product.get("brand"),
            "amazon_price": amazon_price,
            "url": product.get("url"),
            "upc": product.get("upc"),
            "mpn": product.get("mpn"),
            "supplier_name": candidate.get("supplier_name") if candidate else None,
            "supplier_title": candidate.get("supplier_title") if candidate else None,
            "supplier_url": candidate.get("supplier_url") if candidate else None,
            "simulated": bool(product.get("simulated", demo)),
            "match": match_info,
            "profit": profit_info,
        }
        result_items.append(result_item)

        update_scan(
            scan_id,
            progress=i + 1,
            matched=matched_count,
            profitable=profitable_count,
        )

    # Persist all results to store
    fresh = get_scan(scan_id)
    if fresh:
        fresh.results.extend(result_items)
