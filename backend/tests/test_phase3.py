"""
Phase 3 scan API tests.
"""
import threading
import time
import pytest
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer demo-user"}


# ─── Category scan ────────────────────────────────────────────────────────────

def test_create_category_scan():
    r = client.post("/api/scans", json={
        "mode": "category",
        "demo": True,
        "category_config": {
            "category": "Home & Kitchen",
            "max_products": 5,
            "suppliers": ["home_depot", "walmart"],
            "fulfillment_methods": ["amazon_fba"],
            "demo": True,
        }
    }, headers=HEADERS)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["mode"] == "category"
    assert d["status"] in ("queued", "running", "completed")
    assert d["demo"] is True
    return d["id"]


def test_category_scan_bad_category():
    r = client.post("/api/scans", json={
        "mode": "category",
        "demo": True,
        "category_config": {
            "category": "Not A Real Category",
            "max_products": 5,
            "suppliers": ["home_depot"],
            "fulfillment_methods": ["amazon_fba"],
            "demo": True,
        }
    }, headers=HEADERS)
    assert r.status_code == 422  # Validation error


# ─── Seller scan ──────────────────────────────────────────────────────────────

def test_create_seller_scan_demo():
    r = client.post("/api/scans", json={
        "mode": "seller",
        "demo": True,
        "seller_config": {
            "seller_id": "A1TESTSELLERID",
            "max_products": 5,
            "suppliers": ["walmart"],
            "fulfillment_methods": ["amazon_fbm"],
            "demo": True,
        }
    }, headers=HEADERS)
    assert r.status_code == 201, r.text
    assert r.json()["mode"] == "seller"


def test_seller_scan_no_input():
    r = client.post("/api/scans", json={
        "mode": "seller",
        "demo": True,
        "seller_config": {
            "max_products": 5,
            "suppliers": ["walmart"],
            "fulfillment_methods": ["amazon_fbm"],
            "demo": True,
        }
    }, headers=HEADERS)
    assert r.status_code == 422  # Either seller_id or storefront_url required


# ─── Product (ASIN) scan ──────────────────────────────────────────────────────

def test_create_product_scan_asin():
    r = client.post("/api/scans", json={
        "mode": "product",
        "demo": True,
        "product_config": {
            "asin": "B08XYZ1001",
            "suppliers": ["home_depot"],
            "fulfillment_methods": ["amazon_fba"],
            "demo": True,
        }
    }, headers=HEADERS)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["mode"] == "product"


def test_create_product_scan_bad_asin():
    r = client.post("/api/scans", json={
        "mode": "product",
        "demo": True,
        "product_config": {
            "asin": "TOOSHORT",
            "suppliers": ["home_depot"],
            "fulfillment_methods": ["amazon_fba"],
            "demo": True,
        }
    }, headers=HEADERS)
    assert r.status_code == 422  # ASIN must be 10 chars


def test_create_product_scan_url():
    r = client.post("/api/scans", json={
        "mode": "product",
        "demo": True,
        "product_config": {
            "product_url": "https://www.amazon.com/dp/B08XYZ1001",
            "suppliers": ["home_depot"],
            "fulfillment_methods": ["amazon_fba"],
            "demo": True,
        }
    }, headers=HEADERS)
    assert r.status_code == 201, r.text


# ─── Scan lifecycle ───────────────────────────────────────────────────────────

def test_scan_lifecycle_and_progress():
    # Create
    r = client.post("/api/scans", json={
        "mode": "category",
        "demo": True,
        "category_config": {
            "category": "Electronics",
            "max_products": 2,
            "suppliers": ["walmart"],
            "fulfillment_methods": ["amazon_fba"],
            "demo": True,
        }
    }, headers=HEADERS)
    assert r.status_code == 201
    scan_id = r.json()["id"]

    # Poll progress a few times
    for _ in range(10):
        pr = client.get(f"/api/scans/{scan_id}/progress", headers=HEADERS)
        assert pr.status_code == 200
        status = pr.json()["status"]
        if status in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.3)
    assert pr.json()["status"] in ("completed", "failed", "queued", "running")


def test_cancel_scan():
    r = client.post("/api/scans", json={
        "mode": "category",
        "demo": True,
        "category_config": {
            "category": "Pet Supplies",
            "max_products": 1,
            "suppliers": ["walmart"],
            "fulfillment_methods": ["amazon_fba"],
            "demo": True,
        }
    }, headers=HEADERS)
    scan_id = r.json()["id"]
    # Attempt cancel
    cr = client.post(f"/api/scans/{scan_id}/cancel", headers=HEADERS)
    # Might already be completed if worker ran sync – both outcomes OK
    assert cr.status_code in (200, 400)


# ─── Ownership enforcement ────────────────────────────────────────────────────

def test_other_user_cannot_access_scan():
    r = client.post("/api/scans", json={
        "mode": "category",
        "demo": True,
        "category_config": {
            "category": "Sports & Outdoors",
            "max_products": 1,
            "suppliers": ["walmart"],
            "fulfillment_methods": ["amazon_fba"],
            "demo": True,
        }
    }, headers={"Authorization": "Bearer user-A"})
    scan_id = r.json()["id"]
    # Another user tries to access it
    rr = client.get(f"/api/scans/{scan_id}", headers={"Authorization": "Bearer user-B"})
    assert rr.status_code == 403


# ─── Metadata ─────────────────────────────────────────────────────────────────

def test_scan_metadata():
    r = client.get("/api/scans/meta", headers=HEADERS)
    assert r.status_code == 200
    d = r.json()
    assert "categories" in d
    assert "suppliers" in d
    assert "fulfillment_methods" in d
    assert len(d["categories"]) > 0
