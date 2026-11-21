"""
Phase 5 Tests — Supplier Discovery and Product Matching Pipeline.

Verifies:
  - Stage 1: Exact identifier matches (UPC, MPN)
  - Stage 2: Deterministic comparison (brand conflicts, model conflicts, pack count discrepancies, condition)
  - Stage 3: Candidate ranking across multiple supplier options
  - Stage 4: Confidence banding and final decision routing (Strong, Likely, Review, Reject)
  - Supplier discovery and normalization
  - Manual review endpoint (POST /api/scans/{id}/results/{asin}/review)
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-user"}


# ─── Stage 1 & 2: Matching Engine & Critical Mismatch Checks ───────────────────

from app.services.matching import (
    MatchingEngine,
    match_product,
    BAND_STRONG,
    BAND_LIKELY,
    BAND_REVIEW,
    BAND_REJECT,
)


def test_stage1_exact_upc_match():
    az = {
        "title": "Cuisinart 12-Cup Programmable Coffee Maker",
        "brand": "Cuisinart",
        "upc": "086279116918",
        "mpn": "DCC-1200",
    }
    sp = {
        "title": "Cuisinart 12-Cup Coffee Maker DCC-1200",
        "brand": "Cuisinart",
        "upc": "086279116918",
        "mpn": "DCC-1200",
    }
    res = match_product(az, sp)
    assert res["deterministic_score"] >= 95.0
    assert res["confidence_band"] == BAND_STRONG
    assert res["final_decision"] == "accepted"
    assert res["manual_review"] is False
    assert res["match_type"] == "exact"
    assert res["differences"] == []


def test_stage1_exact_mpn_match():
    az = {
        "title": "DEWALT 20V MAX Cordless Drill Combo Kit",
        "brand": "DEWALT",
        "upc": "",
        "mpn": "DCK240C2",
    }
    sp = {
        "title": "DEWALT 2-Tool Cordless Combo Kit",
        "brand": "DEWALT",
        "upc": "",
        "mpn": "DCK240C2",
    }
    res = match_product(az, sp)
    assert res["deterministic_score"] >= 95.0
    assert res["confidence_band"] == BAND_STRONG
    assert res["final_decision"] == "accepted"


def test_stage2_brand_conflict_rejection():
    az = {
        "title": "12-Cup Programmable Coffee Maker",
        "brand": "Cuisinart",
        "upc": "",
        "mpn": "",
    }
    sp = {
        "title": "12-Cup Programmable Coffee Maker",
        "brand": "Hamilton Beach",
        "upc": "",
        "mpn": "",
    }
    res = match_product(az, sp)
    assert res["final_decision"] == "rejected"
    assert res["confidence_band"] == BAND_REJECT
    assert any("Brand conflict" in d for d in res["differences"])


def test_stage2_model_number_conflict_rejection():
    az = {
        "title": "TP-Link Smart WiFi Router Archer A7",
        "brand": "TP-Link",
        "upc": "",
        "mpn": "Archer A7",
    }
    sp = {
        "title": "TP-Link Smart WiFi Router Archer C6",
        "brand": "TP-Link",
        "upc": "",
        "mpn": "Archer C6",
    }
    res = match_product(az, sp)
    assert res["final_decision"] == "rejected"
    assert any("Model number conflict" in d for d in res["differences"])


def test_stage2_pack_count_discrepancy_routes_to_review():
    az = {
        "title": "Brita Water Filter Replacement, 3-Pack",
        "brand": "Brita",
        "package_quantity": 3,
        "upc": "",
        "mpn": "",
    }
    sp = {
        "title": "Brita Water Filter Replacement, Single Filter",
        "brand": "Brita",
        "package_quantity": 1,
        "upc": "",
        "mpn": "",
    }
    res = match_product(az, sp)
    assert any("Package quantity discrepancy" in d for d in res["differences"])
    assert res["confidence_band"] in (BAND_REVIEW, BAND_REJECT)


def test_stage2_condition_conflict():
    az = {
        "title": "Anker 10000mAh Portable Charger",
        "brand": "Anker",
        "condition": "new",
    }
    sp = {
        "title": "Anker 10000mAh Portable Charger (Refurbished)",
        "brand": "Anker",
        "condition": "refurbished",
    }
    res = match_product(az, sp)
    assert any("Condition discrepancy" in d for d in res["differences"])


# ─── Stage 3: Candidate Ranking ───────────────────────────────────────────────

def test_stage3_candidate_ranking():
    az = {
        "title": "DEWALT 20V MAX Cordless Drill Combo Kit",
        "brand": "DEWALT",
        "upc": "028877514573",
        "mpn": "DCK240C2",
    }
    candidates = [
        {
            "supplier_name": "Lowe's",
            "title": "Stanley FatMax Tape Measure",
            "brand": "Stanley",
            "upc": "999999999999",
            "mpn": "FMHT33865S",
        },
        {
            "supplier_name": "Home Depot",
            "title": "DEWALT 20V MAX Cordless Drill Kit DCK240C2",
            "brand": "DEWALT",
            "upc": "028877514573",
            "mpn": "DCK240C2",
        },
        {
            "supplier_name": "Walmart",
            "title": "DEWALT Drill Bits Set 14-Piece",
            "brand": "DEWALT",
            "upc": "111111111111",
            "mpn": "DWA1184",
        },
    ]

    ranked = MatchingEngine.rank_candidates(az, candidates)
    best_candidate, best_match = ranked[0]
    assert best_candidate["supplier_name"] == "Home Depot"
    assert best_match["deterministic_score"] >= 95.0
    assert best_match["final_decision"] == "accepted"


# ─── Supplier Discovery & Normalization ────────────────────────────────────────

from app.services.suppliers.discovery import (
    search_supplier_candidates,
    normalize_supplier_product,
)


def test_supplier_discovery_normalization():
    raw = {
        "supplier_name": "Home Depot",
        "title": "DEWALT Drill",
        "price": "89.99",
        "package_quantity": "1",
    }
    normalized = normalize_supplier_product(raw)
    assert normalized["supplier_name"] == "Home Depot"
    assert normalized["supplier_price"] == 89.99
    assert normalized["package_quantity"] == 1
    assert normalized["condition"] == "new"


def test_search_supplier_candidates_demo():
    product = {
        "asin": "B08XYZ1001",
        "title": "Cuisinart Coffee Maker",
        "supplier_candidates": [
            {
                "supplier_name": "Walmart",
                "supplier_title": "Cuisinart 12-Cup Coffee Maker",
                "supplier_price": 28.50,
            }
        ],
    }
    candidates = search_supplier_candidates(product, demo=True)
    assert len(candidates) >= 1
    assert candidates[0]["supplier_name"] == "Walmart"
    assert candidates[0]["supplier_price"] == 28.50


# ─── Manual Match Review API ──────────────────────────────────────────────────

def _create_and_wait_demo_scan():
    resp = client.post(
        "/api/scans",
        json={
            "mode": "category",
            "category_config": {
                "category": "Home & Kitchen",
                "max_products": 5,
                "demo": True,
            },
            "demo": True,
        },
        headers=AUTH,
    )
    assert resp.status_code == 201
    scan_id = resp.json()["id"]

    import time
    for _ in range(50):
        prog = client.get(f"/api/scans/{scan_id}/progress", headers=AUTH)
        if prog.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    return scan_id


def test_review_match_accept():
    scan_id = _create_and_wait_demo_scan()
    results_resp = client.get(f"/api/scans/{scan_id}/results", headers=AUTH)
    assert results_resp.status_code == 200
    results = results_resp.json()["results"]
    assert len(results) > 0

    target_asin = results[0]["asin"]

    # Submit accept review decision
    rev_resp = client.post(
        f"/api/scans/{scan_id}/results/{target_asin}/review",
        json={"decision": "accepted", "notes": "Verified match manually"},
        headers=AUTH,
    )
    assert rev_resp.status_code == 200
    item = rev_resp.json()
    assert item["match"]["final_decision"] == "accepted"
    assert item["match"]["reviewer_decision"] == "accepted"
    assert item["match"]["reviewer_notes"] == "Verified match manually"
    assert item["match"]["manual_review"] is False
    assert item["match"]["matched"] is True


def test_review_match_reject():
    scan_id = _create_and_wait_demo_scan()
    results_resp = client.get(f"/api/scans/{scan_id}/results", headers=AUTH)
    results = results_resp.json()["results"]
    target_asin = results[0]["asin"]

    rev_resp = client.post(
        f"/api/scans/{scan_id}/results/{target_asin}/review",
        json={"decision": "rejected", "notes": "Variant difference"},
        headers=AUTH,
    )
    assert rev_resp.status_code == 200
    item = rev_resp.json()
    assert item["match"]["final_decision"] == "rejected"
    assert item["match"]["reviewer_decision"] == "rejected"
    assert item["match"]["matched"] is False


def test_review_match_invalid_decision():
    scan_id = _create_and_wait_demo_scan()
    results_resp = client.get(f"/api/scans/{scan_id}/results", headers=AUTH)
    target_asin = results_resp.json()["results"][0]["asin"]

    bad_resp = client.post(
        f"/api/scans/{scan_id}/results/{target_asin}/review",
        json={"decision": "maybe"},
        headers=AUTH,
    )
    assert bad_resp.status_code == 422


def test_review_match_not_found():
    scan_id = _create_and_wait_demo_scan()
    resp = client.post(
        f"/api/scans/{scan_id}/results/NONEXISTENT/review",
        json={"decision": "accepted"},
        headers=AUTH,
    )
    assert resp.status_code == 404


def test_review_match_forbidden_wrong_user():
    scan_id = _create_and_wait_demo_scan()
    results_resp = client.get(f"/api/scans/{scan_id}/results", headers=AUTH)
    target_asin = results_resp.json()["results"][0]["asin"]

    wrong_user_resp = client.post(
        f"/api/scans/{scan_id}/results/{target_asin}/review",
        json={"decision": "accepted"},
        headers={"Authorization": "Bearer stranger"},
    )
    assert wrong_user_resp.status_code == 403
