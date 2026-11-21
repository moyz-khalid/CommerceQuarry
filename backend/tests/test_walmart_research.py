"""
Walmart Seller Research Test Suite (Milestone 1).
Validates URL parsing, product normalization, demo & CSV providers,
API endpoints, and end-to-end scan orchestration.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.walmart import (
    parse_walmart_seller_url,
    normalize_walmart_product,
    DemoWalmartProvider,
    CsvWalmartProvider,
    get_walmart_provider,
    DEMO_SELLERS,
)
from app.services.sourcing.scan_store import get_scan

client = TestClient(app)


# ─── Phase 2: URL Parsing Tests ───────────────────────────────────────────────

def test_parse_walmart_seller_standard_url():
    res = parse_walmart_seller_url("https://www.walmart.com/seller/101001")
    assert res["valid"] is True
    assert res["seller_id"] == "101001"
    assert "https://www.walmart.com/seller/101001" in res["storefront_url"]
    assert res["error"] is None


def test_parse_walmart_seller_query_param_url():
    res = parse_walmart_seller_url("https://www.walmart.com/seller?sellerId=994821")
    assert res["valid"] is True
    assert res["seller_id"] == "994821"


def test_parse_walmart_seller_browse_url():
    res = parse_walmart_seller_url("https://www.walmart.com/browse/seller/F4B892")
    assert res["valid"] is True
    assert res["seller_id"] == "F4B892"


def test_parse_walmart_seller_direct_id():
    res = parse_walmart_seller_url("101001")
    assert res["valid"] is True
    assert res["seller_id"] == "101001"
    assert "https://www.walmart.com/seller/101001" in res["storefront_url"]


def test_parse_walmart_seller_invalid_domain():
    res = parse_walmart_seller_url("https://www.amazon.com/seller/101001")
    assert res["valid"] is False
    assert "walmart.com" in res["error"]


def test_parse_walmart_seller_empty():
    res = parse_walmart_seller_url("")
    assert res["valid"] is False
    assert "cannot be empty" in res["error"]


# ─── Phase 4: Product Normalization Tests ─────────────────────────────────────

def test_normalize_walmart_product():
    raw = {
        "walmart_product_id": "WM-9901",
        "product_title": "Test DeWalt Kit",
        "current_price": "$129.99",
        "original_price": "149.00",
        "brand": "DeWalt",
        "upc": "028877514573",
        "package_quantity": "2",
        "weight_lbs": "8.5",
    }
    p = normalize_walmart_product(raw, provider_name="test_provider", is_demo=True)
    assert p.walmart_product_id == "WM-9901"
    assert p.product_title == "Test DeWalt Kit"
    assert p.current_price == 129.99
    assert p.original_price == 149.00
    assert p.brand == "DeWalt"
    assert p.upc == "028877514573"
    assert p.package_quantity == 2
    assert p.weight_lbs == 8.5
    assert p.is_demo is True
    # Test dictionary compatibility
    d = p.to_dict()
    assert d["title"] == "Test DeWalt Kit"
    assert d["price"] == 129.99
    assert d["asin"] == "WM-9901"


def test_normalize_walmart_product_missing_values_safe():
    raw = {"id": "WM-0001", "name": "Basic Item"}
    p = normalize_walmart_product(raw)
    assert p.walmart_product_id == "WM-0001"
    assert p.current_price == 0.0
    assert p.original_price is None
    assert p.upc is None
    assert p.model_number is None
    assert p.weight_lbs is None
    assert p.package_quantity == 1


# ─── Phase 12: Demo Provider Tests ───────────────────────────────────────────

def test_demo_walmart_provider():
    provider = DemoWalmartProvider()
    seller = provider.identify_seller("https://www.walmart.com/seller/101001")
    assert seller is not None
    assert seller.seller_id == "101001"
    assert seller.seller_name == "ProTools & Hardware Depot"
    assert seller.is_demo is True

    # Retrieve products
    products, total = provider.get_seller_products("101001", limit=10, page=1)
    assert len(products) > 0
    assert total == len(DEMO_SELLERS["101001"]["products"])
    for p in products:
        assert p.is_demo is True
        assert p.current_price > 0
        assert p.product_title != ""


def test_demo_walmart_provider_filters():
    provider = DemoWalmartProvider()
    # Filter by price
    products, _ = provider.get_seller_products("101001", min_price=50.0, max_price=100.0)
    for p in products:
        assert 50.0 <= p.current_price <= 100.0


# ─── Phase 3: CSV Provider Tests ──────────────────────────────────────────────

def test_csv_walmart_provider():
    sample_csv = """walmart_product_id,product_title,current_price,brand,upc
WM-C01,Custom Impact Driver,$89.99,Craftsman,012345678901
WM-C02,Laser Distance Measure,45.00,Bosch,012345678902
"""
    provider = CsvWalmartProvider.from_csv_text(sample_csv)
    products, total = provider.get_seller_products("csv_upload")
    assert total == 2
    assert products[0].walmart_product_id == "WM-C01"
    assert products[0].current_price == 89.99
    assert products[0].brand == "Craftsman"
    assert products[1].current_price == 45.00


# ─── API Endpoints Tests ──────────────────────────────────────────────────────

def test_api_parse_seller_url():
    resp = client.post("/api/walmart/parse-seller-url", json={"url_or_id": "https://www.walmart.com/seller/101001"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["seller_id"] == "101001"
    assert data["is_demo"] is True


def test_api_list_demo_sellers():
    resp = client.get("/api/walmart/demo-sellers")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    assert any(s["seller_id"] == "101001" for s in data)


def test_api_list_providers():
    resp = client.get("/api/walmart/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    provider_ids = [p["id"] for p in data["providers"]]
    assert "demo" in provider_ids
    assert "serpapi" in provider_ids
    assert "apify" in provider_ids
    assert "csv" in provider_ids


def test_api_launch_walmart_seller_scan():
    payload = {
        "seller_id": "101001",
        "storefront_url": "https://www.walmart.com/seller/101001",
        "provider": "demo",
        "max_products": 5,
        "suppliers": ["home_depot", "lowes", "aliexpress"],
        "fulfillment_methods": ["walmart_wfs", "walmart_sf"],
        "demo": True,
    }
    resp = client.post(
        "/api/walmart/seller-scan",
        json=payload,
        headers={"Authorization": "Bearer demo-user"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mode"] == "walmart_seller"
    assert data["status"] in ("queued", "running", "completed")

    # Verify background execution completes and populates results
    import time
    from uuid import UUID
    scan_id = UUID(data["id"])
    time.sleep(1.0)
    scan = get_scan(scan_id)
    assert scan is not None
    assert scan.progress > 0
    assert len(scan.results) > 0
    first_res = scan.results[0]
    assert "walmart_price" in first_res or "amazon_price" in first_res
    assert "profit" in first_res
    assert "match" in first_res
