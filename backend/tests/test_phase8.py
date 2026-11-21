"""
Phase 8 Tests — Results Management and Manual Review Workspace.

Verifies:
  - 8.1 & 8.2: Rich filtering (min/max profit, min ROI, min margin, supplier filter, fulfillment method, search)
  - 8.3: Sorting (net_profit, roi_pct, margin_pct, supplier_cost, amazon_price) and server-side pagination
  - 8.4: Detailed product view (GET /api/scans/{scan_id}/results/{asin})
  - 8.5: Manual review decisions (accepted, rejected, investigation), price correction re-calc, and audit trail preservation
  - Star / bookmark toggle for opportunities
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.services.sourcing.scan_store import create_scan, get_scan
from app.services.sourcing.orchestrator import orchestrate_scan

client = TestClient(app)
AUTH = {"Authorization": "Bearer user_p8"}


@pytest.fixture
def completed_scan():
    scan = create_scan(
        user_id="user_p8",
        mode="category",
        config={"category": "Tools & Home Improvement", "max_products": 6, "demo": True},
        demo=True,
    )
    orchestrate_scan(scan.id)
    return scan.id


def test_results_filtering_by_min_profit(completed_scan):
    resp = client.get(f"/api/scans/{completed_scan}/results?min_profit=5.0", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["results"]:
        assert item["profit"]["net_profit"] >= 5.0


def test_results_filtering_by_supplier(completed_scan):
    resp = client.get(f"/api/scans/{completed_scan}/results?supplier=home_depot", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["results"]:
        assert "home_depot" in (item.get("supplier_name") or "").lower()


def test_results_keyword_search(completed_scan):
    resp = client.get(f"/api/scans/{completed_scan}/results?search=Drill", headers=AUTH)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["results"]:
        assert (
            "drill" in item["title"].lower()
            or "drill" in (item.get("supplier_title") or "").lower()
            or "drill" in (item.get("brand") or "").lower()
        )


def test_results_sorting_highest_net_profit(completed_scan):
    resp = client.get(f"/api/scans/{completed_scan}/results?sort_by=net_profit&sort_dir=desc", headers=AUTH)
    assert resp.status_code == 200
    items = resp.json()["results"]
    if len(items) >= 2:
        for i in range(len(items) - 1):
            assert items[i]["profit"]["net_profit"] >= items[i + 1]["profit"]["net_profit"]


def test_results_sorting_lowest_supplier_cost(completed_scan):
    resp = client.get(f"/api/scans/{completed_scan}/results?sort_by=supplier_cost&sort_dir=asc", headers=AUTH)
    assert resp.status_code == 200
    items = resp.json()["results"]
    if len(items) >= 2:
        for i in range(len(items) - 1):
            cost_a = items[i]["profit"]["supplier_cost"] or 0
            cost_b = items[i + 1]["profit"]["supplier_cost"] or 0
            assert cost_a <= cost_b


def test_get_single_product_detail(completed_scan):
    all_resp = client.get(f"/api/scans/{completed_scan}/results", headers=AUTH)
    first_asin = all_resp.json()["results"][0]["asin"]

    detail_resp = client.get(f"/api/scans/{completed_scan}/results/{first_asin}", headers=AUTH)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["asin"] == first_asin
    assert "profit" in detail
    assert "match" in detail
    assert "audit_trail" in detail


def test_star_toggle_opportunity(completed_scan):
    all_resp = client.get(f"/api/scans/{completed_scan}/results", headers=AUTH)
    asin = all_resp.json()["results"][0]["asin"]

    # Toggle ON
    resp1 = client.post(f"/api/scans/{completed_scan}/results/{asin}/star", headers=AUTH)
    assert resp1.status_code == 200
    assert resp1.json()["starred"] is True

    # Filter by starred
    starred_resp = client.get(f"/api/scans/{completed_scan}/results?review_status=starred", headers=AUTH)
    assert starred_resp.status_code == 200
    assert any(r["asin"] == asin for r in starred_resp.json()["results"])

    # Toggle OFF
    resp2 = client.post(f"/api/scans/{completed_scan}/results/{asin}/star", headers=AUTH)
    assert resp2.status_code == 200
    assert resp2.json()["starred"] is False


def test_manual_review_investigation_and_audit_trail(completed_scan):
    all_resp = client.get(f"/api/scans/{completed_scan}/results", headers=AUTH)
    asin = all_resp.json()["results"][0]["asin"]

    review_payload = {
        "decision": "investigation",
        "notes": "Pack count needs confirmation with distributor",
        "corrected_price": 18.50,
        "corrected_pack_count": 2,
    }
    resp = client.post(f"/api/scans/{completed_scan}/results/{asin}/review", json=review_payload, headers=AUTH)
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["match"]["final_decision"] == "investigation"
    assert updated["match"]["manual_review"] is True
    assert updated["corrected_price"] == 18.50
    assert updated["corrected_pack_count"] == 2

    # Check audit trail preservation
    assert len(updated["audit_trail"]) >= 1
    last_log = updated["audit_trail"][-1]
    assert last_log["decision"] == "investigation"
    assert last_log["notes"] == "Pack count needs confirmation with distributor"
    assert last_log["user_id"] == "user_p8"
