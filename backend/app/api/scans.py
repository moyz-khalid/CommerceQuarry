"""
Scan API router (Phase 3 — full sourcing workflow).
Replaces the previous in-memory placeholder.
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Response, Query, Depends
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.schemas.scan_schemas import (
    ScanCreateRequest,
    ScanResponse,
    ScanProgressResponse,
    ScanResultItem,
    ScanResultsResponse,
    MatchInfo,
    MatchReviewRequest,
    ProfitInfo,
    AMAZON_CATEGORIES,
    SUPPORTED_SUPPLIERS,
    FULFILLMENT_METHODS,
)
from app.services.sourcing.scan_store import (
    create_scan,
    get_scan,
    list_scans,
    update_scan,
    cancel_scan,
)
from app.services.exports import (
    export_scan_results_csv,
    export_scan_results_xlsx,
)
from app.auth import get_current_user
from fastapi import Depends

router = APIRouter()


# ─── Helper ───────────────────────────────────────────────────────────────────

def _enqueue(scan_id: UUID):
    """
    Attempt to enqueue the scan via Celery.
    Falls back to synchronous in-process execution if Celery/Redis is unavailable,
    so the API stays functional without a running worker.
    """
    try:
        from app.workers.worker import run_scan
        run_scan.delay(str(scan_id))
    except Exception:
        # Celery not available — run synchronously in a background thread
        import threading
        from app.services.sourcing.orchestrator import orchestrate_scan
        def _run():
            try:
                orchestrate_scan(scan_id)
                from datetime import datetime as _dt
                update_scan(scan_id, status="completed", completed_at=_dt.utcnow())
            except Exception as e:
                update_scan(scan_id, status="failed", error_summary=str(e),
                            completed_at=datetime.utcnow())
        threading.Thread(target=_run, daemon=True).start()


def _scan_to_response(scan) -> ScanResponse:
    return ScanResponse(
        id=scan.id,
        user_id=scan.user_id,
        mode=scan.mode,
        status=scan.status,
        progress=scan.progress,
        total=scan.total,
        matched=scan.matched,
        profitable=scan.profitable,
        error_summary=scan.error_summary,
        demo=scan.demo,
        created_at=scan.created_at,
        updated_at=scan.updated_at,
        completed_at=scan.completed_at,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/scans/meta")
def get_scan_metadata():
    """Return supported categories, suppliers, and fulfillment methods."""
    return {
        "categories": AMAZON_CATEGORIES,
        "suppliers": SUPPORTED_SUPPLIERS,
        "fulfillment_methods": FULFILLMENT_METHODS,
    }


@router.post("/scans", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
def create_new_scan(
    req: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    """
    Validate the scan request, persist the scan record, enqueue the background job,
    and return the scan ID immediately.
    """
    # Build serialisable config dict from mode-specific config
    if req.mode == "category":
        if not req.category_config:
            if req.config:
                cfg = dict(req.config)
            else:
                raise HTTPException(400, "category_config is required for category mode")
        else:
            cfg = req.category_config.dict()
    elif req.mode == "seller":
        if not req.seller_config:
            if req.config:
                cfg = dict(req.config)
            else:
                raise HTTPException(400, "seller_config is required for seller mode")
        else:
            cfg = req.seller_config.dict()
    elif req.mode == "walmart_seller":
        if not req.walmart_seller_config:
            if req.config:
                cfg = dict(req.config)
            else:
                cfg = {}
        else:
            cfg = req.walmart_seller_config.dict()
    elif req.mode == "product":
        if not req.product_config:
            if req.config:
                cfg = dict(req.config)
            else:
                raise HTTPException(400, "product_config is required for product mode")
        else:
            pc = req.product_config
            cfg = pc.dict()
            cfg["resolved_asin"] = pc.resolved_asin()
    else:
        raise HTTPException(400, f"Unsupported mode: {req.mode}")

    cfg["demo"] = req.demo
    scan = create_scan(user_id=user_id, mode=req.mode, config=cfg, demo=req.demo)

    # Enqueue via background tasks (non-blocking)
    background_tasks.add_task(_enqueue, scan.id)

    return _scan_to_response(scan)


@router.get("/scans", response_model=list[ScanResponse])
def list_user_scans(user_id: str = Depends(get_current_user)):
    """List all scans belonging to the current user."""
    return [_scan_to_response(s) for s in list_scans(user_id)]


@router.get("/scans/{scan_id}", response_model=ScanResponse)
def get_scan_detail(scan_id: UUID, user_id: str = Depends(get_current_user)):
    """Get a specific scan (must belong to the requesting user)."""
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")
    return _scan_to_response(scan)


@router.get("/scans/{scan_id}/progress", response_model=ScanProgressResponse)
def get_scan_progress(scan_id: UUID, user_id: str = Depends(get_current_user)):
    """Lightweight progress poll endpoint for the frontend."""
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")
    return ScanProgressResponse(
        id=scan.id,
        status=scan.status,
        progress=scan.progress,
        total=scan.total,
        matched=scan.matched,
        profitable=scan.profitable,
        error_summary=scan.error_summary,
    )


@router.post("/scans/{scan_id}/cancel", response_model=ScanResponse)
def cancel_user_scan(scan_id: UUID, user_id: str = Depends(get_current_user)):
    """Cancel a queued or running scan."""
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")
    if scan.status not in ("queued", "running"):
        raise HTTPException(400, f"Cannot cancel a scan in state '{scan.status}'")
    updated = cancel_scan(scan_id)
    return _scan_to_response(updated)


# ─── Phase 4, 8 & 9: Results & Export Endpoints ───────────────────────────────

def _build_scan_result_item(r: dict) -> ScanResultItem:
    """Helper to consistently serialize a raw result dict into ScanResultItem."""
    m = r.get("match", {})
    p = r.get("profit", {})
    return ScanResultItem(
        asin=r.get("asin", ""),
        title=r.get("title", ""),
        brand=r.get("brand"),
        amazon_price=float(r.get("amazon_price", 0)),
        url=r.get("url"),
        image_url=r.get("image_url") or r.get("image"),
        upc=r.get("upc"),
        mpn=r.get("mpn"),
        supplier_name=r.get("supplier_name"),
        supplier_title=r.get("supplier_title"),
        supplier_url=r.get("supplier_url"),
        supplier_image_url=r.get("supplier_image_url"),
        simulated=bool(r.get("simulated", False)),
        starred=bool(r.get("starred", False)),
        audit_trail=r.get("audit_trail") or [],
        corrected_price=r.get("corrected_price"),
        corrected_pack_count=r.get("corrected_pack_count"),
        match=MatchInfo(
            matched=bool(m.get("matched", False)),
            confidence=m.get("confidence", "none"),
            score=float(m.get("score", 0.0)),
            match_method=m.get("match_method", "none"),
            mismatch_reason=m.get("mismatch_reason"),
            deterministic_score=m.get("deterministic_score"),
            confidence_band=m.get("confidence_band"),
            match_type=m.get("match_type"),
            explanation=m.get("explanation"),
            differences=m.get("differences") or [],
            manual_review=bool(m.get("manual_review", False)),
            final_decision=m.get("final_decision", "accepted"),
            reviewer_decision=m.get("reviewer_decision"),
            reviewer_notes=m.get("reviewer_notes"),
            engine_version=m.get("engine_version"),
            ai_verified=bool(m.get("ai_verified", False)),
            ai_score=m.get("ai_score"),
            ai_decision=m.get("ai_decision"),
            ai_reason=m.get("ai_reason"),
            ai_differences=m.get("ai_differences") or [],
            tokens_used=m.get("tokens_used"),
            ai_cost_usd=m.get("ai_cost_usd"),
        ),
        profit=ProfitInfo(
            profitable=bool(p.get("profitable", False)),
            net_profit=float(p.get("net_profit", 0.0)),
            roi_pct=float(p.get("roi_pct", 0.0)),
            margin_pct=float(p.get("margin_pct", 0.0)),
            referral_fee=float(p.get("referral_fee", 0.0)),
            fba_fee=float(p.get("fba_fee", 0.0)),
            total_fees=float(p.get("total_fees", 0.0)),
            total_cost=float(p.get("total_cost", 0.0)),
            break_even_price=float(p.get("break_even_price", 0.0)),
            total_profit=float(p.get("total_profit", 0.0)),
            supplier_cost=p.get("supplier_cost"),
            simulated=p.get("simulated"),
            best_fulfillment_method=p.get("best_fulfillment_method", "amazon_fba"),
            calculation_status=p.get("calculation_status", "verified"),
            fulfillment_breakdown=p.get("fulfillment_breakdown"),
            itemized_expenses=p.get("itemized_expenses"),
        ),
    )


@router.get("/scans/{scan_id}/results", response_model=ScanResultsResponse)
def get_scan_results(
    scan_id: UUID,
    user_id: str = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
    min_profit: Optional[float] = None,
    max_profit: Optional[float] = None,
    min_roi: Optional[float] = None,
    min_margin: Optional[float] = None,
    min_amazon_price: Optional[float] = None,
    max_amazon_price: Optional[float] = None,
    min_supplier_price: Optional[float] = None,
    max_supplier_price: Optional[float] = None,
    supplier: Optional[str] = None,
    confidence: Optional[str] = None,
    match_type: Optional[str] = None,
    fulfillment_method: Optional[str] = None,
    calculation_status: Optional[str] = None,
    review_status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = "desc",
):
    """
    Return filtered, sorted, and paginated results for a completed scan.
    """
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")
    if scan.status not in ("completed", "completed_with_errors", "running"):
        raise HTTPException(
            400,
            f"Results not yet available — scan is in state '{scan.status}'. "
            "Poll /progress until status is 'completed'.",
        )

    filtered = list(scan.results)

    # 1. Filters
    if min_profit is not None:
        filtered = [r for r in filtered if float(r.get("profit", {}).get("net_profit", 0)) >= min_profit]
    if max_profit is not None:
        filtered = [r for r in filtered if float(r.get("profit", {}).get("net_profit", 0)) <= max_profit]
    if min_roi is not None:
        filtered = [r for r in filtered if float(r.get("profit", {}).get("roi_pct", 0)) >= min_roi]
    if min_margin is not None:
        filtered = [r for r in filtered if float(r.get("profit", {}).get("margin_pct", 0)) >= min_margin]
    if min_amazon_price is not None:
        filtered = [r for r in filtered if float(r.get("amazon_price", 0)) >= min_amazon_price]
    if max_amazon_price is not None:
        filtered = [r for r in filtered if float(r.get("amazon_price", 0)) <= max_amazon_price]
    if min_supplier_price is not None:
        filtered = [r for r in filtered if float(r.get("profit", {}).get("supplier_cost", 0) or 0) >= min_supplier_price]
    if max_supplier_price is not None:
        filtered = [r for r in filtered if float(r.get("profit", {}).get("supplier_cost", 0) or 0) <= max_supplier_price]
    if supplier:
        filtered = [r for r in filtered if supplier.lower() in str(r.get("supplier_name", "")).lower()]
    if confidence:
        filtered = [r for r in filtered if str(r.get("match", {}).get("confidence", "")).lower() == confidence.lower()]
    if match_type:
        filtered = [r for r in filtered if str(r.get("match", {}).get("match_type") or r.get("match", {}).get("match_method", "")).lower() == match_type.lower()]
    if fulfillment_method:
        filtered = [r for r in filtered if str(r.get("profit", {}).get("best_fulfillment_method", "")).lower() == fulfillment_method.lower()]
    if calculation_status:
        filtered = [r for r in filtered if str(r.get("profit", {}).get("calculation_status", "")).lower() == calculation_status.lower()]

    if review_status:
        rev = review_status.lower()
        if rev in ("review_needed", "review"):
            filtered = [r for r in filtered if r.get("match", {}).get("manual_review") or r.get("match", {}).get("final_decision") in ("review", "investigation")]
        elif rev in ("approved", "accepted"):
            filtered = [r for r in filtered if r.get("match", {}).get("final_decision") == "accepted"]
        elif rev == "rejected":
            filtered = [r for r in filtered if r.get("match", {}).get("final_decision") == "rejected"]
        elif rev == "investigation":
            filtered = [r for r in filtered if r.get("match", {}).get("final_decision") == "investigation"]
        elif rev == "starred":
            filtered = [r for r in filtered if r.get("starred")]

    if search:
        q = search.lower()
        filtered = [
            r for r in filtered
            if q in str(r.get("title", "")).lower()
            or q in str(r.get("asin", "")).lower()
            or q in str(r.get("brand", "")).lower()
            or q in str(r.get("upc", "")).lower()
            or q in str(r.get("mpn", "")).lower()
            or q in str(r.get("supplier_title", "")).lower()
        ]

    # 2. Sorting
    if sort_by:
        reverse = (sort_dir.lower() != "asc")
        if sort_by == "net_profit":
            filtered.sort(key=lambda r: float(r.get("profit", {}).get("net_profit", 0)), reverse=reverse)
        elif sort_by == "roi_pct":
            filtered.sort(key=lambda r: float(r.get("profit", {}).get("roi_pct", 0)), reverse=reverse)
        elif sort_by == "margin_pct":
            filtered.sort(key=lambda r: float(r.get("profit", {}).get("margin_pct", 0)), reverse=reverse)
        elif sort_by == "supplier_cost":
            filtered.sort(key=lambda r: float(r.get("profit", {}).get("supplier_cost", 0) or 0), reverse=reverse)
        elif sort_by == "amazon_price":
            filtered.sort(key=lambda r: float(r.get("amazon_price", 0)), reverse=reverse)
        elif sort_by == "match_score":
            filtered.sort(key=lambda r: float(r.get("match", {}).get("score", 0)), reverse=reverse)

    total_filtered = len(filtered)
    paged = filtered[offset : offset + limit]

    review_count = sum(
        1 for r in scan.results
        if r.get("match", {}).get("manual_review") or r.get("match", {}).get("final_decision") in ("review", "investigation")
    )

    return ScanResultsResponse(
        scan_id=scan.id,
        status=scan.status,
        total_results=total_filtered,
        matched_count=scan.matched,
        profitable_count=scan.profitable,
        review_count=review_count,
        results=[_build_scan_result_item(r) for r in paged],
    )


@router.get("/scans/{scan_id}/results/{asin}", response_model=ScanResultItem)
def get_scan_result_detail(
    scan_id: UUID,
    asin: str,
    user_id: str = Depends(get_current_user),
):
    """
    Get detailed product view for a single ASIN including side-by-side comparison,
    full fee breakdowns across all 4 fulfillment methods, and audit trail history.
    """
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")

    for item in scan.results:
        if item.get("asin") == asin:
            return _build_scan_result_item(item)

    raise HTTPException(404, f"Product with ASIN '{asin}' not found in scan results")


@router.post("/scans/{scan_id}/results/{asin}/star")
def toggle_star_result(
    scan_id: UUID,
    asin: str,
    user_id: str = Depends(get_current_user),
):
    """
    Toggle starred status for a sourcing opportunity.
    """
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")

    for item in scan.results:
        if item.get("asin") == asin:
            current = bool(item.get("starred", False))
            item["starred"] = not current
            return {"asin": asin, "starred": item["starred"]}

    raise HTTPException(404, f"Product with ASIN '{asin}' not found in scan results")


@router.post("/scans/{scan_id}/results/{asin}/review", response_model=ScanResultItem)
def review_match_result(
    scan_id: UUID,
    asin: str,
    review_req: MatchReviewRequest,
    user_id: str = Depends(get_current_user),
):
    """
    Submit reviewer decision ('accepted', 'rejected', or 'investigation'), notes,
    and optional price/pack count corrections with complete audit log preservation.
    """
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")

    target_item = None
    for item in scan.results:
        if item.get("asin") == asin:
            target_item = item
            break

    if not target_item:
        raise HTTPException(404, f"Product with ASIN '{asin}' not found in scan results")

    # Update match record
    m = target_item.setdefault("match", {})
    m["reviewer_decision"] = review_req.decision
    m["reviewer_notes"] = review_req.notes
    m["final_decision"] = review_req.decision

    if review_req.decision == "accepted":
        m["matched"] = True
        m["manual_review"] = False
    elif review_req.decision == "rejected":
        m["matched"] = False
        m["manual_review"] = False
    else:  # investigation
        m["manual_review"] = True

    # Audit trail entry
    trail = target_item.setdefault("audit_trail", [])
    trail.append({
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "decision": review_req.decision,
        "notes": review_req.notes,
        "corrected_price": review_req.corrected_price,
        "corrected_pack_count": review_req.corrected_pack_count,
    })

    # Optional price/pack correction re-calculation
    if review_req.corrected_price is not None and review_req.corrected_price > 0:
        target_item["corrected_price"] = review_req.corrected_price
        from app.services.profitability import calculate_all_fulfillment_methods
        new_profit = calculate_all_fulfillment_methods(
            amazon_price=float(target_item.get("amazon_price", 0)),
            cost_price=float(review_req.corrected_price),
            weight_lbs=target_item.get("weight_lbs"),
            dimensions_str=target_item.get("dimensions"),
        )
        target_item["profit"] = new_profit

    if review_req.corrected_pack_count is not None:
        target_item["corrected_pack_count"] = review_req.corrected_pack_count

    # Re-calculate scan matched & profitable counts
    scan.matched = sum(1 for r in scan.results if r.get("match", {}).get("matched"))
    scan.profitable = sum(1 for r in scan.results if r.get("profit", {}).get("profitable") and r.get("match", {}).get("matched"))

    return _build_scan_result_item(target_item)


# ─── Phase 6: DeepSeek AI Verification on Demand ─────────────────────────────

@router.post("/scans/{scan_id}/results/{asin}/verify-ai", response_model=ScanResultItem)
def trigger_ai_verification(
    scan_id: UUID,
    asin: str,
    user_id: str = Depends(get_current_user),
):
    """
    On-demand AI verification using DeepSeek for an ambiguous or disputed candidate.
    """
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")

    target_item = None
    for item in scan.results:
        if item.get("asin") == asin:
            target_item = item
            break

    if not target_item:
        raise HTTPException(404, f"Product with ASIN '{asin}' not found in scan results")

    from app.services.ai import verify_candidate_match

    m = target_item.get("match", {})
    supplier_prod = {
        "supplier_name": target_item.get("supplier_name"),
        "supplier_title": target_item.get("supplier_title"),
        "supplier_price": target_item.get("profit", {}).get("supplier_cost", 0),
        "supplier_url": target_item.get("supplier_url"),
        "upc": target_item.get("upc"),
        "mpn": target_item.get("mpn"),
    }

    # Force AI verification
    updated_match = verify_candidate_match(target_item, supplier_prod, m, force=True)
    target_item["match"] = updated_match

    # Re-calculate scan matched count
    scan.matched = sum(1 for r in scan.results if r.get("match", {}).get("matched"))
    scan.profitable = sum(1 for r in scan.results if r.get("profit", {}).get("profitable") and r.get("match", {}).get("matched"))

    return _build_scan_result_item(target_item)


# ─── Phase 4 & 9: Export endpoint ─────────────────────────────────────────────

@router.get("/scans/{scan_id}/export")
def export_scan_results(
    scan_id: UUID,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    user_id: str = Depends(get_current_user),
    profitable_only: bool = False,
    include_rejected: bool = True,
    supplier: Optional[str] = None,
    selected_asins: Optional[str] = None,
    starred_only: bool = False,
):
    """
    Export scan results in CSV or Excel (.xlsx) format with filtering options.
    """
    scan = get_scan(scan_id)
    if not scan:
        raise HTTPException(404, "Scan not found")
    if scan.user_id != user_id:
        raise HTTPException(403, "Forbidden")
    if scan.status not in ("completed", "completed_with_errors", "running"):
        raise HTTPException(
            400,
            f"Cannot export results for scan in status '{scan.status}'. Must be completed.",
        )

    export_items = list(scan.results)

    # Filtering for export
    if profitable_only:
        export_items = [r for r in export_items if r.get("profit", {}).get("profitable")]
    if not include_rejected:
        export_items = [r for r in export_items if r.get("match", {}).get("final_decision") != "rejected"]
    if supplier:
        export_items = [r for r in export_items if supplier.lower() in str(r.get("supplier_name", "")).lower()]
    if selected_asins:
        asins_set = {a.strip() for a in selected_asins.split(",") if a.strip()}
        if asins_set:
            export_items = [r for r in export_items if r.get("asin") in asins_set]
    if starred_only:
        export_items = [r for r in export_items if r.get("starred")]

    if format == "xlsx":
        meta = {
            "mode": scan.mode,
            "created_at": str(scan.created_at),
            "completed_at": str(scan.completed_at),
        }
        xlsx_bytes = export_scan_results_xlsx(export_items, scan_id=str(scan.id), scan_meta=meta)
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="scan_{scan_id}_results.xlsx"'},
        )
    else:
        csv_data = export_scan_results_csv(export_items)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="scan_{scan_id}_results.csv"'},
        )
