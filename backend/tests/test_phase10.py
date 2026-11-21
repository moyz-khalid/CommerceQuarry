"""
Phase 10 Tests — Live Amazon Integration.

Verifies:
  - 10.1 & 10.2: Amazon provider interface, capabilities check, and error resilience
  - 10.3: Normalization into internal AmazonProduct schema
  - 10.4: Failure behavior (unsupported seller inventory, missing fields)
  - Factory pattern and integration health endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.amazon import (
    AmazonProduct,
    DemoAmazonProvider,
    RainforestAmazonProvider,
    get_amazon_provider,
)

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-user"}


def test_amazon_product_normalization():
    p = AmazonProduct(
        asin="B08N5WRWNW",
        title="Sample Wireless Headphones",
        brand="SoundCore",
        price=39.99,
        url="https://www.amazon.com/dp/B08N5WRWNW",
        upc="086279116918",
        mpn="SC-WH01",
    )
    d = p.to_dict()
    assert d["asin"] == "B08N5WRWNW"
    assert d["amazon_price"] == 39.99
    assert d["brand"] == "SoundCore"


def test_demo_amazon_provider_capabilities():
    provider = DemoAmazonProvider()
    caps = provider.check_capabilities()
    assert caps["lookup_asin"] is True
    assert caps["category_discovery"] is True
    assert caps["seller_inventory"] is True

    test_res = provider.test_connection()
    assert test_res["connected"] is True
    assert test_res["provider"] == "demo"


def test_demo_amazon_provider_lookups():
    provider = DemoAmazonProvider()

    # ASIN lookup
    prod = provider.lookup_asin("B08N5WRWNW")
    assert prod is not None
    assert prod.asin == "B08N5WRWNW"
    assert prod.price > 0

    # URL lookup
    prod_url = provider.lookup_url("https://www.amazon.com/dp/B08N5WRWNW")
    assert prod_url is not None
    assert prod_url.asin == "B08N5WRWNW"

    # Category discovery
    items = provider.discover_category("Tools & Home Improvement", max_products=3)
    assert len(items) > 0
    assert items[0].price > 0


def test_rainforest_amazon_provider_reports_seller_unsupported():
    provider = RainforestAmazonProvider(api_key="")
    caps = provider.check_capabilities()
    assert caps["configured"] is False
    assert caps["seller_inventory"] is False  # Explicitly unsupported without SP-API

    # Calling seller inventory should raise NotImplementedError
    with pytest.raises(NotImplementedError) as exc:
        provider.get_seller_inventory("SELLER123")
    assert "Seller inventory retrieval is not supported" in str(exc.value)


def test_amazon_provider_factory():
    demo_p = get_amazon_provider("demo")
    assert isinstance(demo_p, DemoAmazonProvider)

    rf_p = get_amazon_provider("rainforest")
    assert isinstance(rf_p, RainforestAmazonProvider)


def test_api_amazon_capabilities_and_test_endpoints():
    cap_resp = client.get("/api/integrations/amazon/capabilities")
    assert cap_resp.status_code == 200
    data = cap_resp.json()
    assert "capabilities" in data
    assert "lookup_asin" in data["capabilities"]

    test_resp = client.post("/api/integrations/amazon/test")
    assert test_resp.status_code == 200
    assert "connected" in test_resp.json()
