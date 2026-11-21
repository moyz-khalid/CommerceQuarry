import pytest
import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.main import app

client = TestClient(app)


def test_root_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_scan():
    resp = client.post(
        "/api/scans",
        json={"config": {"mode": "category", "parameters": {}}},
        headers={"Authorization": "Bearer demo-user"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "queued"
    assert data["mode"] == "category"
    assert data["user_id"] == "demo-user"


def test_list_scans():
    # Create one first
    client.post(
        "/api/scans",
        json={"config": {"mode": "seller", "parameters": {}}},
        headers={"Authorization": "Bearer test-user"},
    )
    resp = client.get("/api/scans", headers={"Authorization": "Bearer test-user"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_fee_profile():
    resp = client.post(
        "/api/fee-profiles",
        json={"name": "Amazon FBA Standard", "description": "Standard FBA fees"},
        headers={"Authorization": "Bearer demo-user"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Amazon FBA Standard"


def test_list_fee_profiles():
    resp = client.get("/api/fee-profiles", headers={"Authorization": "Bearer demo-user"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_integration():
    resp = client.post(
        "/api/integrations",
        json={"name": "Home Depot", "config": {"api_key": "demo"}},
        headers={"Authorization": "Bearer demo-user"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Home Depot"


def test_get_settings():
    resp = client.get("/api/settings/demo-user", headers={"Authorization": "Bearer demo-user"})
    assert resp.status_code == 200
    data = resp.json()
    assert "default_scan_mode" in data


def test_update_settings():
    resp = client.put(
        "/api/settings/demo-user",
        json={"default_scan_mode": "product", "max_products": 50, "min_profit": 10.0, "min_roi": 25.0},
        headers={"Authorization": "Bearer demo-user"},
    )
    assert resp.status_code == 200
    assert resp.json()["default_scan_mode"] == "product"
