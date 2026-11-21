"""
Phase 4 Part 1 tests — matching service, profitability service,
orchestrator result persistence, and results API endpoint.
"""
import pytest
from uuid import uuid4


# ─── Matching service ─────────────────────────────────────────────────────────

from app.services.matching import (
    match_product,
    match_product_demo,
    MATCH_EXACT,
    MATCH_HIGH,
    MATCH_MEDIUM,
    MATCH_NONE,
)


def test_match_exact_upc():
    az = {"upc": "086279116918", "title": "Coffee Maker", "mpn": ""}
    sp = {"upc": "086279116918", "title": "Coffee Maker Model X", "mpn": ""}
    result = match_product(az, sp)
    assert result["matched"] is True
    assert result["confidence"] == MATCH_EXACT
    assert result["match_method"] == "upc"


def test_match_exact_mpn():
    az = {"upc": "", "title": "Cordless Drill", "mpn": "DCK240C2"}
    sp = {"upc": "", "title": "Power Drill Kit", "mpn": "DCK240C2"}
    result = match_product(az, sp)
    assert result["matched"] is True
    assert result["confidence"] == MATCH_EXACT
    assert result["match_method"] == "mpn"


def test_match_high_title_similarity():
    az = {"upc": "", "title": "Hydro Flask 32 oz Water Bottle Wide Mouth", "mpn": ""}
    sp = {"upc": "", "title": "Hydro Flask 32 oz Wide Mouth Water Bottle", "mpn": ""}
    result = match_product(az, sp)
    assert result["matched"] is True
    assert result["confidence"] == MATCH_HIGH
    assert result["score"] >= 0.80


def test_match_medium_title_similarity():
    az = {"upc": "", "title": "Hydro Flask 32 oz Water Bottle Wide Mouth", "mpn": ""}
    sp = {"upc": "", "title": "Hydro Flask 32oz Wide Mouth Water Bottle", "mpn": ""}
    result = match_product(az, sp)
    assert result["matched"] is True
    assert result["confidence"] == MATCH_MEDIUM


def test_match_none_unrelated_titles():
    az = {"upc": "", "title": "Coffee Maker Stainless Steel", "mpn": ""}
    sp = {"upc": "", "title": "Yoga Mat Non-Slip Exercise", "mpn": ""}
    result = match_product(az, sp)
    assert result["matched"] is False
    assert result["confidence"] == MATCH_NONE


def test_match_product_demo_matched_flag():
    product = {"title": "Demo Item", "matched": True}
    result = match_product_demo(product)
    assert result["matched"] is True
    assert result["match_method"] == "demo_stub"


def test_match_product_demo_unmatched_flag():
    product = {"title": "Demo Item", "matched": False}
    result = match_product_demo(product)
    assert result["matched"] is False


# ─── Profitability service ────────────────────────────────────────────────────

from app.services.profitability import (
    calculate_profitability,
    calculate_profitability_demo,
)


def test_profitability_profitable():
    result = calculate_profitability(amazon_price=50.0, cost_price=20.0)
    assert result["profitable"] is True
    assert result["net_profit"] > 0
    assert 0 < result["roi_pct"] <= 200
    assert 0 < result["margin_pct"] <= 100


def test_profitability_not_profitable():
    # Cost higher than selling price
    result = calculate_profitability(amazon_price=10.0, cost_price=15.0)
    assert result["profitable"] is False
    assert result["net_profit"] < 0


def test_profitability_break_even_above_cost():
    result = calculate_profitability(amazon_price=50.0, cost_price=20.0)
    assert result["break_even_price"] > result["total_cost"]


def test_profitability_demo_uses_60_pct_cost():
    product = {"price": 50.0, "profitable": True}
    result = calculate_profitability_demo(product)
    assert result["supplier_cost"] == pytest.approx(30.0)
    assert result["simulated"] is True
    assert result["profitable"] is True


def test_profitability_demo_respects_profitable_false():
    product = {"price": 50.0, "profitable": False}
    result = calculate_profitability_demo(product)
    assert result["profitable"] is False


def test_profitability_total_profit_scales_with_units():
    result = calculate_profitability(amazon_price=50.0, cost_price=20.0, units=10)
    single = calculate_profitability(amazon_price=50.0, cost_price=20.0, units=1)
    assert result["total_profit"] == pytest.approx(single["net_profit"] * 10, rel=1e-4)


# ─── Orchestrator result persistence ─────────────────────────────────────────

from app.services.sourcing.scan_store import create_scan, get_scan
from app.services.sourcing.orchestrator import orchestrate_scan


def test_orchestrator_demo_category_produces_results():
    scan = create_scan(
        user_id="user_p4_test",
        mode="category",
        config={"category": "Electronics", "max_products": 10, "demo": True},
        demo=True,
    )
    orchestrate_scan(scan.id)
    updated = get_scan(scan.id)
    assert updated.status == "completed"
    assert len(updated.results) > 0

    item = updated.results[0]
    assert "asin" in item
    assert "match" in item
    assert "profit" in item
    assert isinstance(item["match"]["matched"], bool)
    assert isinstance(item["profit"]["net_profit"], float)


def test_orchestrator_demo_product_scan_produces_results():
    scan = create_scan(
        user_id="user_p4_test",
        mode="product",
        config={"asin": "B08XYZ6001", "resolved_asin": "B08XYZ6001", "demo": True},
        demo=True,
    )
    orchestrate_scan(scan.id)
    updated = get_scan(scan.id)
    assert updated.status == "completed"
    assert len(updated.results) == 1
    assert updated.results[0]["asin"] == "B08XYZ6001"


def test_orchestrator_matched_profitable_counters_match_results():
    scan = create_scan(
        user_id="user_p4_counter",
        mode="category",
        config={"category": "Home & Kitchen", "max_products": 10, "demo": True},
        demo=True,
    )
    orchestrate_scan(scan.id)
    updated = get_scan(scan.id)

    actual_matched = sum(1 for r in updated.results if r["match"]["matched"])
    actual_profitable = sum(1 for r in updated.results if r["profit"]["profitable"])
    assert updated.matched == actual_matched
    assert updated.profitable == actual_profitable


# ─── Results API endpoint ─────────────────────────────────────────────────────

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer user_results_test"}


def _create_demo_scan(mode="category", config=None, auth=AUTH):
    if config is None:
        config = {
            "category_config": {
                "category": "Electronics",
                "demo": True,
            },
            "demo": True,
        }
    return client.post("/api/scans", json={"mode": mode, **config}, headers=auth)


def test_results_endpoint_returns_200_after_completion():
    # Create a scan and wait for it to complete (synchronous fallback thread)
    resp = _create_demo_scan()
    assert resp.status_code == 201
    scan_id = resp.json()["id"]

    # Poll until completed (up to 5 s)
    import time
    for _ in range(50):
        prog = client.get(f"/api/scans/{scan_id}/progress", headers=AUTH)
        if prog.json()["status"] == "completed":
            break
        time.sleep(0.1)

    results_resp = client.get(f"/api/scans/{scan_id}/results", headers=AUTH)
    assert results_resp.status_code == 200
    body = results_resp.json()
    assert body["scan_id"] == scan_id
    assert body["status"] == "completed"
    assert body["total_results"] > 0
    assert isinstance(body["results"], list)


def test_results_endpoint_item_shape():
    resp = _create_demo_scan()
    scan_id = resp.json()["id"]

    import time
    for _ in range(50):
        prog = client.get(f"/api/scans/{scan_id}/progress", headers=AUTH)
        if prog.json()["status"] == "completed":
            break
        time.sleep(0.1)

    results_resp = client.get(f"/api/scans/{scan_id}/results", headers=AUTH)
    item = results_resp.json()["results"][0]
    assert "asin" in item
    assert "amazon_price" in item
    assert "match" in item
    assert "profit" in item
    assert "matched" in item["match"]
    assert "net_profit" in item["profit"]


def test_results_endpoint_requires_auth():
    resp = _create_demo_scan()
    scan_id = resp.json()["id"]
    no_auth = client.get(f"/api/scans/{scan_id}/results")
    assert no_auth.status_code in (401, 403)


def test_results_endpoint_404_for_unknown_scan():
    resp = client.get(f"/api/scans/{uuid4()}/results", headers=AUTH)
    assert resp.status_code == 404


def test_results_endpoint_403_for_wrong_user():
    resp = _create_demo_scan()
    scan_id = resp.json()["id"]

    import time
    for _ in range(50):
        prog = client.get(f"/api/scans/{scan_id}/progress", headers=AUTH)
        if prog.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    wrong = client.get(f"/api/scans/{scan_id}/results",
                       headers={"Authorization": "Bearer other_user"})
    assert wrong.status_code == 403


def test_results_pagination():
    resp = _create_demo_scan()
    scan_id = resp.json()["id"]

    import time
    for _ in range(50):
        prog = client.get(f"/api/scans/{scan_id}/progress", headers=AUTH)
        if prog.json()["status"] == "completed":
            break
        time.sleep(0.1)

    all_resp = client.get(f"/api/scans/{scan_id}/results?limit=100&offset=0", headers=AUTH)
    total = all_resp.json()["total_results"]

    page1 = client.get(f"/api/scans/{scan_id}/results?limit=1&offset=0", headers=AUTH)
    assert len(page1.json()["results"]) == min(1, total)
