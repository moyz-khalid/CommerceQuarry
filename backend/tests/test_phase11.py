"""
Phase 11 Tests — Live Supplier Integrations.

Verifies:
  - 11.1: Adapter interface and implementations for Home Depot, Walmart, Lowe's, AliExpress
  - 11.2: Multi-supplier 8-stage search sequence and candidate ranking
  - 11.3: Supplier integration status, latency, and capability reporting endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.suppliers import (
    SupplierCandidate,
    HomeDepotAdapter,
    WalmartAdapter,
    LowesAdapter,
    AliExpressAdapter,
    execute_multi_supplier_search,
    ADAPTER_MAP,
)

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-user"}


def test_all_four_supplier_adapters_registered():
    assert "home_depot" in ADAPTER_MAP
    assert "walmart" in ADAPTER_MAP
    assert "lowes" in ADAPTER_MAP
    assert "aliexpress" in ADAPTER_MAP


def test_supplier_adapters_capabilities():
    hd = HomeDepotAdapter()
    wm = WalmartAdapter()
    lw = LowesAdapter()
    ali = AliExpressAdapter()

    assert hd.get_capabilities()["upc_search"] is True
    assert wm.get_capabilities()["upc_search"] is True
    assert lw.get_capabilities()["upc_search"] is True
    assert ali.get_capabilities()["upc_search"] is False  # AliExpress lacks UPC indexing


def test_multi_supplier_search_sequence_and_deduplication():
    amz_product = {
        "asin": "B08N5WRWNW",
        "title": "DeWalt 20V Cordless Drill Driver Kit",
        "brand": "DeWalt",
        "price": 99.00,
        "upc": "086279116918",
        "mpn": "DCD771C2",
        "model_number": "DCD771C2",
    }

    candidates = execute_multi_supplier_search(
        amazon_product=amz_product,
        selected_suppliers=["home_depot", "walmart", "lowes", "aliexpress"],
    )

    assert len(candidates) > 0
    # Deduplication test: all (supplier_name, supplier_product_id) pairs must be unique
    keys = [(c["supplier_name"], c.get("supplier_product_id")) for c in candidates]
    assert len(keys) == len(set(keys))

    # All candidates must have required schema keys
    for c in candidates:
        assert "supplier_name" in c
        assert "supplier_title" in c
        assert "supplier_price" in c
        assert c["supplier_price"] > 0


def test_candidate_ranking_prioritizes_exact_identifier_match():
    amz_product = {
        "asin": "B08N5WRWNW",
        "title": "DeWalt Cordless Drill Kit",
        "price": 100.0,
        "upc": "086279116918",
        "mpn": "DCD771C2",
    }

    candidates = execute_multi_supplier_search(
        amazon_product=amz_product,
        selected_suppliers=["home_depot", "walmart"],
    )

    # Top candidate should have exact UPC match or exact MPN match
    top = candidates[0]
    assert top["upc"] == "086279116918" or top["mpn"] == "DCD771C2"


def test_api_suppliers_status_endpoint():
    resp = client.get("/api/integrations/suppliers/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "suppliers" in data
    suppliers_list = [s["supplier"] for s in data["suppliers"]]
    assert "home_depot" in suppliers_list
    assert "walmart" in suppliers_list
    assert "lowes" in suppliers_list
    assert "aliexpress" in suppliers_list


def test_api_test_individual_supplier_endpoint():
    resp_hd = client.post("/api/integrations/suppliers/home_depot/test")
    assert resp_hd.status_code == 200
    assert resp_hd.json()["supplier"] == "home_depot"

    resp_wm = client.post("/api/integrations/suppliers/walmart/test")
    assert resp_wm.status_code == 200
    assert resp_wm.json()["supplier"] == "walmart"

    # Invalid supplier returns 404
    resp_inv = client.post("/api/integrations/suppliers/unknown_vendor/test")
    assert resp_inv.status_code == 404
