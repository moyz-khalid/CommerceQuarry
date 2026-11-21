"""
Phase 4 Part 2 tests — Exports (CSV, XLSX), advanced matching heuristics
(pack counts, model conflicts), multi-supplier candidate discovery, and export API.
"""
import pytest
import io
import csv
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
import openpyxl

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-user"}


# ─── Matching Scenarios (Section 4.2) ──────────────────────────────────────────

from app.services.matching import (
    match_product,
    extract_pack_count,
    MATCH_EXACT,
    MATCH_HIGH,
    MATCH_LOW,
    MATCH_NONE,
)


def test_extract_pack_count():
    assert extract_pack_count("Brita Standard Water Filter Replacement, 3-Pack") == 3
    assert extract_pack_count("AA Batteries Pack of 12 Alkaline") == 12
    assert extract_pack_count("LED Light Bulbs 4 pk 60W Equivalent") == 4
    assert extract_pack_count("Single Replacement Unit") is None


def test_pack_count_discrepancy_penalty():
    az = {
        "title": "Brita Water Filter Replacement, 3-Pack",
        "upc": "",
        "mpn": "",
        "package_quantity": 3,
    }
    sp = {
        "title": "Brita Water Filter Replacement Single",
        "upc": "",
        "mpn": "",
        "package_quantity": 1,
    }
    result = match_product(az, sp)
    assert result["matched"] is False
    assert result["confidence"] == MATCH_LOW
    assert "Pack count discrepancy" in (result.get("mismatch_reason") or "")


def test_model_number_conflict():
    az = {
        "title": "Cuisinart 12-Cup Coffee Maker",
        "upc": "",
        "mpn": "DCC-1200",
    }
    sp = {
        "title": "Cuisinart 12-Cup Coffee Maker",
        "upc": "",
        "mpn": "DCC-3200",
    }
    result = match_product(az, sp)
    assert result["matched"] is False
    assert result["confidence"] == MATCH_NONE
    assert "Model/MPN conflict" in (result.get("mismatch_reason") or "")


def test_matching_preserves_exact_identifiers():
    az = {
        "title": "DEWALT 20V MAX Cordless Drill Combo Kit",
        "upc": "028877514573",
        "mpn": "DCK240C2",
    }
    sp = {
        "title": "DEWALT 20V MAX Cordless Compact Drill (2-Tool)",
        "upc": "028877514573",
        "mpn": "DCK240C2",
    }
    result = match_product(az, sp)
    assert result["matched"] is True
    assert result["confidence"] == MATCH_EXACT


# ─── Multi-Supplier Candidate Discovery ───────────────────────────────────────

from app.services.sourcing.demo_provider import (
    demo_category_products,
    demo_find_supplier_candidates,
)


def test_demo_find_supplier_candidates():
    products = demo_category_products("Home & Kitchen", 5)
    assert len(products) > 0
    coffee_maker = products[0]
    candidates = demo_find_supplier_candidates(coffee_maker)
    assert len(candidates) > 0
    candidate = candidates[0]
    assert "supplier_name" in candidate
    assert "supplier_price" in candidate
    assert candidate["supplier_name"] in ("Walmart", "Home Depot", "Lowe's", "AliExpress")


def test_demo_find_supplier_candidates_filtered_by_supplier():
    products = demo_category_products("Tools & Home Improvement", 5)
    drill = products[0]
    candidates = demo_find_supplier_candidates(drill, selected_suppliers=["home_depot"])
    assert len(candidates) > 0
    assert any("Home Depot" in c["supplier_name"] for c in candidates)


# ─── Export Service (Section 4.3 item 12) ─────────────────────────────────────

from app.services.exports import export_scan_results_csv, export_scan_results_xlsx


@pytest.fixture
def sample_results():
    return [
        {
            "asin": "B08XYZ1001",
            "title": "Cuisinart 12-Cup Coffee Maker",
            "brand": "Cuisinart",
            "amazon_price": 49.99,
            "url": "https://www.amazon.com/dp/B08XYZ1001",
            "supplier_name": "Walmart",
            "supplier_title": "Cuisinart 12-Cup Coffee Maker DCC-1200",
            "simulated": True,
            "match": {
                "matched": True,
                "confidence": "EXACT",
                "score": 1.0,
                "match_method": "upc",
                "mismatch_reason": None,
            },
            "profit": {
                "profitable": True,
                "net_profit": 7.39,
                "roi_pct": 25.9,
                "margin_pct": 14.8,
                "break_even_price": 50.25,
                "supplier_cost": 28.50,
            },
        },
        {
            "asin": "B07XYZ1002",
            "title": "AmazonBasics Microwave",
            "brand": "AmazonBasics",
            "amazon_price": 59.99,
            "url": "https://www.amazon.com/dp/B07XYZ1002",
            "supplier_name": "Home Depot",
            "supplier_title": "Magic Chef Microwave",
            "simulated": True,
            "match": {
                "matched": False,
                "confidence": "NONE",
                "score": 0.0,
                "match_method": "none",
                "mismatch_reason": "No meaningful overlap",
            },
            "profit": {
                "profitable": False,
                "net_profit": -12.50,
                "roi_pct": -19.5,
                "margin_pct": -20.8,
                "break_even_price": 75.00,
                "supplier_cost": 64.00,
            },
        },
    ]


def test_export_csv_generation(sample_results):
    csv_str = export_scan_results_csv(sample_results)
    assert isinstance(csv_str, str)
    assert len(csv_str) > 0

    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) == 3  # 1 header + 2 items
    headers = rows[0]
    assert "ASIN" in headers
    assert "Product Title" in headers
    assert "Amazon Price ($)" in headers
    assert "Net Profit ($)" in headers
    assert "ROI (%)" in headers
    assert "Simulated" in headers

    row1 = rows[1]
    assert row1[0] == "B08XYZ1001"
    assert "Cuisinart" in row1[1]


def test_export_xlsx_generation(sample_results):
    xlsx_bytes = export_scan_results_xlsx(sample_results, scan_id="test-scan-id")
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 0

    # Load with openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb.active
    assert ws.title == "Scan Results"
    assert ws.max_row == 3  # header + 2 rows
    assert ws.max_column >= 10

    # Check header
    header_val = ws.cell(row=1, column=1).value
    assert header_val == "ASIN"

    # Check data row
    asin_val = ws.cell(row=2, column=1).value
    assert asin_val == "B08XYZ1001"


# ─── Export API Endpoints ─────────────────────────────────────────────────────

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


def test_api_export_csv():
    scan_id = _create_and_wait_demo_scan()
    resp = client.get(f"/api/scans/{scan_id}/export?format=csv", headers=AUTH)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Content-Disposition" in resp.headers
    assert f'filename="scan_{scan_id}_results.csv"' in resp.headers["Content-Disposition"]
    assert "ASIN" in resp.text
    assert "Product Title" in resp.text


def test_api_export_xlsx():
    scan_id = _create_and_wait_demo_scan()
    resp = client.get(f"/api/scans/{scan_id}/export?format=xlsx", headers=AUTH)
    assert resp.status_code == 200
    assert "openxmlformats" in resp.headers["content-type"]
    assert "Content-Disposition" in resp.headers
    assert f'filename="scan_{scan_id}_results.xlsx"' in resp.headers["Content-Disposition"]

    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    assert wb.active.title == "Scan Results"
    assert wb.active.max_row >= 2


def test_api_export_unauthorized():
    scan_id = _create_and_wait_demo_scan()
    resp = client.get(f"/api/scans/{scan_id}/export?format=csv")
    assert resp.status_code in (401, 403)


def test_api_export_forbidden_wrong_user():
    scan_id = _create_and_wait_demo_scan()
    resp = client.get(
        f"/api/scans/{scan_id}/export?format=csv",
        headers={"Authorization": "Bearer stranger"},
    )
    assert resp.status_code == 403


def test_api_export_not_found():
    resp = client.get(f"/api/scans/{uuid4()}/export?format=csv", headers=AUTH)
    assert resp.status_code == 404
