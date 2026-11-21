"""
Phase 7 Tests — Profitability Calculator and Fee Profiles.

Verifies:
  - Section 7.1 & 7.2: Independent P&L for all 4 fulfillment methods:
      1. Amazon FBA
      2. Amazon FBM
      3. Walmart WFS
      4. Walmart Seller-Fulfilled
  - Section 7.3: Core formulas, break-even price, zero-division guards, and missing cost handling
  - Section 7.4: Fee profiles CRUD, duplication, and default profile selection
  - Section 7.5: Calculation status (verified, estimated, incomplete) and itemized expense tracking
  - Integration with scan results and exports
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-user"}


# ─── 7.1 & 7.2: Four Fulfillment Methods ──────────────────────────────────────

from app.services.profitability import (
    calculate_method_pnl,
    calculate_all_fulfillment_methods,
)


def test_amazon_fba_pnl_calculation():
    res = calculate_method_pnl(
        method="amazon_fba",
        selling_price=50.0,
        product_cost=20.0,
        weight_lbs=1.5,
        dimensions_str="8.0 x 6.0 x 4.0 in",
    )
    assert res["method"] == "amazon_fba"
    assert res["net_profit"] > 0
    assert res["roi_pct"] > 0
    assert res["margin_pct"] > 0
    assert res["break_even_price"] > 20.0
    assert res["calculation_status"] == "verified"
    fees = res["itemized_fees"]
    assert fees["referral_fee"] == pytest.approx(7.50)  # 15% of $50
    assert fees["fulfillment_fee"] > 0
    assert fees["inbound_shipping"] > 0


def test_amazon_fbm_pnl_calculation():
    res = calculate_method_pnl(
        method="amazon_fbm",
        selling_price=50.0,
        product_cost=20.0,
        weight_lbs=1.5,
    )
    assert res["method"] == "amazon_fbm"
    fees = res["itemized_fees"]
    assert fees["fulfillment_fee"] == 0.0  # FBM has no FBA fee
    assert fees["outbound_shipping"] > 0   # Outbound shipping present
    assert fees["labor_handling"] > 0      # Warehouse handling present


def test_walmart_wfs_pnl_calculation():
    res = calculate_method_pnl(
        method="walmart_wfs",
        selling_price=45.0,
        product_cost=15.0,
        weight_lbs=2.0,
    )
    assert res["method"] == "walmart_wfs"
    assert res["net_profit"] > 0
    fees = res["itemized_fees"]
    assert fees["fulfillment_fee"] == pytest.approx(3.45)


def test_walmart_seller_fulfilled_pnl_calculation():
    res = calculate_method_pnl(
        method="walmart_sf",
        selling_price=45.0,
        product_cost=15.0,
        weight_lbs=2.0,
    )
    assert res["method"] == "walmart_sf"
    assert res["itemized_fees"]["outbound_shipping"] > 0


def test_all_four_methods_evaluated_and_best_picked():
    res = calculate_all_fulfillment_methods(
        amazon_price=60.0,
        cost_price=22.0,
        weight_lbs=1.2,
        dimensions_str="6.0 x 4.0 x 2.0 in",
    )
    assert "best_fulfillment_method" in res
    assert res["best_fulfillment_method"] in ["amazon_fba", "amazon_fbm", "walmart_wfs", "walmart_sf"]
    assert "fulfillment_breakdown" in res
    breakdown = res["fulfillment_breakdown"]
    assert len(breakdown) == 4
    for m in ["amazon_fba", "amazon_fbm", "walmart_wfs", "walmart_sf"]:
        assert m in breakdown
        assert "net_profit" in breakdown[m]
        assert "roi_pct" in breakdown[m]


# ─── 7.3: Zero-Division Safety & Missing Cost Handling ────────────────────────

def test_missing_product_cost_incomplete_status():
    res = calculate_method_pnl(
        method="amazon_fba",
        selling_price=40.0,
        product_cost=0.0,  # Missing cost
    )
    assert res["calculation_status"] == "incomplete"
    assert res["roi_pct"] == 0.0  # Division by zero avoided
    assert res["profitable"] is False


def test_zero_selling_price_safe():
    res = calculate_method_pnl(
        method="amazon_fba",
        selling_price=0.0,
        product_cost=10.0,
    )
    assert res["margin_pct"] == 0.0
    assert res["net_profit"] < 0
    assert res["profitable"] is False


def test_missing_weight_dimensions_estimated_status():
    res = calculate_method_pnl(
        method="amazon_fba",
        selling_price=35.0,
        product_cost=15.0,
        weight_lbs=None,  # Missing weight
        dimensions_str=None,  # Missing dimensions
    )
    assert res["calculation_status"] == "estimated"
    assert res["net_profit"] > 0


# ─── 7.4: Fee Profiles CRUD & Defaults ────────────────────────────────────────

def test_fee_profiles_list_seeds_defaults():
    resp = client.get("/api/fee-profiles", headers=AUTH)
    assert resp.status_code == 200
    profiles = resp.json()
    assert len(profiles) >= 4
    methods = [p["fulfillment_method"] for p in profiles]
    assert "amazon_fba" in methods
    assert "amazon_fbm" in methods
    assert "walmart_wfs" in methods
    assert "walmart_sf" in methods


def test_create_and_read_fee_profile():
    create_payload = {
        "name": "Custom FBA Heavy Duty",
        "description": "Special oversized profile",
        "fulfillment_method": "amazon_fba",
        "referral_fee_pct": 12.0,
        "fulfillment_fee_flat": 6.50,
        "inbound_shipping_per_lb": 0.60,
        "prep_cost_per_unit": 2.00,
        "packaging_cost_per_unit": 1.00,
        "storage_fee_monthly_per_cuft": 1.20,
        "handling_per_order": 0.50,
        "misc_overhead_flat": 0.50,
        "is_default": False,
    }
    resp = client.post("/api/fee-profiles", json=create_payload, headers=AUTH)
    assert resp.status_code == 201
    created = resp.json()
    p_id = created["id"]
    assert created["name"] == "Custom FBA Heavy Duty"
    assert created["fulfillment_fee_flat"] == 6.50

    # Get by ID
    get_resp = client.get(f"/api/fee-profiles/{p_id}", headers=AUTH)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Custom FBA Heavy Duty"


def test_update_fee_profile():
    # Create profile
    resp = client.post(
        "/api/fee-profiles",
        json={"name": "To Update", "fulfillment_method": "amazon_fba"},
        headers=AUTH,
    )
    p_id = resp.json()["id"]

    # Update
    up_resp = client.put(
        f"/api/fee-profiles/{p_id}",
        json={"name": "Updated Name", "fulfillment_fee_flat": 4.10},
        headers=AUTH,
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["name"] == "Updated Name"
    assert up_resp.json()["fulfillment_fee_flat"] == 4.10


def test_duplicate_fee_profile():
    resp = client.post(
        "/api/fee-profiles",
        json={"name": "Original Profile", "fulfillment_method": "amazon_fba"},
        headers=AUTH,
    )
    p_id = resp.json()["id"]

    dup_resp = client.post(f"/api/fee-profiles/{p_id}/duplicate", headers=AUTH)
    assert dup_resp.status_code == 201
    dup = dup_resp.json()
    assert dup["id"] != p_id
    assert "Original Profile (Copy)" in dup["name"]


def test_set_profile_as_default():
    resp = client.post(
        "/api/fee-profiles",
        json={"name": "New Default FBA", "fulfillment_method": "amazon_fba", "is_default": False},
        headers=AUTH,
    )
    p_id = resp.json()["id"]

    def_resp = client.post(f"/api/fee-profiles/{p_id}/set-default", headers=AUTH)
    assert def_resp.status_code == 200
    assert def_resp.json()["is_default"] is True


def test_delete_fee_profile():
    resp = client.post(
        "/api/fee-profiles",
        json={"name": "To Delete", "fulfillment_method": "amazon_fbm"},
        headers=AUTH,
    )
    p_id = resp.json()["id"]

    del_resp = client.delete(f"/api/fee-profiles/{p_id}", headers=AUTH)
    assert del_resp.status_code == 204

    # Verify gone
    get_resp = client.get(f"/api/fee-profiles/{p_id}", headers=AUTH)
    assert get_resp.status_code == 404


# ─── 7.5: Scan Results Include Phase 7 P&L Metadata ───────────────────────────

def test_scan_results_contain_fulfillment_breakdown():
    resp = client.post(
        "/api/scans",
        json={
            "mode": "category",
            "category_config": {
                "category": "Tools & Home Improvement",
                "max_products": 3,
                "demo": True,
            },
            "demo": True,
        },
        headers=AUTH,
    )
    scan_id = resp.json()["id"]

    import time
    for _ in range(50):
        prog = client.get(f"/api/scans/{scan_id}/progress", headers=AUTH)
        if prog.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    results_resp = client.get(f"/api/scans/{scan_id}/results", headers=AUTH)
    assert results_resp.status_code == 200
    items = results_resp.json()["results"]
    assert len(items) > 0
    profit = items[0]["profit"]
    assert "best_fulfillment_method" in profit
    assert "calculation_status" in profit
    assert profit["best_fulfillment_method"] in ["amazon_fba", "amazon_fbm", "walmart_wfs", "walmart_sf"]
