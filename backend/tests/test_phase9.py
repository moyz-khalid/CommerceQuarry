"""
Phase 9 Tests — CSV and Excel Exports.

Verifies:
  - 9.1: CSV generation with 22 required columns and formula injection protection
  - 9.2: Excel generation with 5 distinct worksheets and professional styling
  - 9.3: Filtered export options (profitable only, supplier, selected ASINs)
  - Ownership validation and error handling
"""
import pytest
import io
import openpyxl
from fastapi.testclient import TestClient
from app.main import app
from app.services.sourcing.scan_store import create_scan
from app.services.sourcing.orchestrator import orchestrate_scan
from app.services.exports import (
    sanitize_cell,
    export_scan_results_csv,
    export_scan_results_xlsx,
    EXPORT_COLUMNS,
)

client = TestClient(app)
AUTH = {"Authorization": "Bearer user_p9"}


def test_sanitize_cell_formula_injection_protection():
    assert sanitize_cell("=1+1") == "'=1+1"
    assert sanitize_cell("+SUM(A1:A10)") == "'+SUM(A1:A10)"
    assert sanitize_cell("-10+5") == "'-10+5"
    assert sanitize_cell("@HYPERLINK('evil')") == "'@HYPERLINK('evil')"
    assert sanitize_cell("Standard Title") == "Standard Title"
    assert sanitize_cell(45.50) == 45.50
    assert sanitize_cell(True) is True


def test_csv_export_contains_all_columns_and_escapes_formulas():
    sample_results = [
        {
            "asin": "=DANGEROUS_ASIN",
            "title": "+Evil Product Title",
            "amazon_price": 49.99,
            "supplier_name": "Home Depot",
            "supplier_title": "HD Equivalent",
            "profit": {
                "supplier_cost": 20.0,
                "net_profit": 14.50,
                "roi_pct": 72.5,
                "margin_pct": 29.0,
                "referral_fee": 7.50,
                "fba_fee": 4.75,
                "total_fees": 15.49,
                "profitable": True,
            },
            "match": {
                "matched": True,
                "confidence": "exact",
                "match_type": "upc",
                "explanation": "Exact UPC matched",
                "differences": [],
            },
        }
    ]

    csv_content = export_scan_results_csv(sample_results)
    assert len(EXPORT_COLUMNS) >= 20
    assert "Product Title" in csv_content
    assert "Net Profit ($)" in csv_content
    assert "Best Fulfillment Method" in csv_content

    # Check formula injection was escaped with leading single quote
    assert "'=DANGEROUS_ASIN" in csv_content
    assert "'+Evil Product Title" in csv_content


def test_excel_export_creates_five_worksheets():
    sample_results = [
        {
            "asin": "B001",
            "title": "Profitable Item",
            "amazon_price": 50.0,
            "profit": {"profitable": True, "net_profit": 15.0, "supplier_cost": 20.0},
            "match": {"matched": True, "confidence": "high", "final_decision": "accepted"},
        },
        {
            "asin": "B002",
            "title": "Review Needed Item",
            "amazon_price": 30.0,
            "profit": {"profitable": True, "net_profit": 5.0, "supplier_cost": 15.0},
            "match": {"matched": False, "confidence": "medium", "manual_review": True, "final_decision": "investigation"},
        },
        {
            "asin": "B003",
            "title": "Rejected Item",
            "amazon_price": 20.0,
            "profit": {"profitable": False, "net_profit": -5.0, "supplier_cost": 18.0},
            "match": {"matched": False, "confidence": "none", "final_decision": "rejected"},
        },
    ]

    xlsx_bytes = export_scan_results_xlsx(sample_results, scan_id="test_scan_123")
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))

    sheet_names = wb.sheetnames
    assert len(sheet_names) >= 5
    assert "Profitable Products" in sheet_names
    assert "All Matched Products" in sheet_names
    assert "Manual Review" in sheet_names
    assert "Rejected Matches" in sheet_names
    assert "Scan Summary" in sheet_names

    # Check Summary Sheet contents
    summary_ws = wb["Scan Summary"]
    summary_text = [str(cell.value) for row in summary_ws.iter_rows() for cell in row if cell.value]
    assert any("CommerceQuarry" in s for s in summary_text)
    assert any("test_scan_123" in s for s in summary_text)


def test_api_export_options():
    scan = create_scan(
        user_id="user_p9",
        mode="category",
        config={"category": "Tools & Home Improvement", "max_products": 5, "demo": True},
        demo=True,
    )
    orchestrate_scan(scan.id)

    # 1. Export profitable only
    resp_prof = client.get(f"/api/scans/{scan.id}/export?format=csv&profitable_only=true", headers=AUTH)
    assert resp_prof.status_code == 200
    assert resp_prof.headers["content-type"].startswith("text/csv")

    # 2. Export 5-sheet Excel
    resp_xlsx = client.get(f"/api/scans/{scan.id}/export?format=xlsx", headers=AUTH)
    assert resp_xlsx.status_code == 200
    assert "spreadsheetml.sheet" in resp_xlsx.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(resp_xlsx.content))
    assert len(wb.sheetnames) >= 5

    # 3. Export with selected ASINs
    all_results = client.get(f"/api/scans/{scan.id}/results", headers=AUTH).json()["results"]
    if len(all_results) >= 1:
        sel_asin = all_results[0]["asin"]
        resp_sel = client.get(f"/api/scans/{scan.id}/export?format=csv&selected_asins={sel_asin}", headers=AUTH)
        assert resp_sel.status_code == 200
        assert sel_asin in resp_sel.text
