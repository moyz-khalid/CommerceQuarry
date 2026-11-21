from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from uuid import UUID, uuid4
from typing import List, Dict, Any, Optional

from app.auth import get_current_user
from app.services.amazon import get_amazon_provider
from app.services.suppliers import ADAPTER_MAP

router = APIRouter()

_integrations: dict[UUID, dict] = {}


class IntegrationCreate(BaseModel):
    name: str
    config: dict


class Integration(BaseModel):
    id: UUID
    name: str
    config: dict


@router.post("/integrations", response_model=Integration, status_code=201)
def create_integration(integ: IntegrationCreate):
    integ_id = uuid4()
    record = {"id": integ_id, "name": integ.name, "config": integ.config}
    _integrations[integ_id] = record
    return record


@router.get("/integrations", response_model=List[Integration])
def list_integrations():
    return list(_integrations.values())


@router.get("/integrations/{integration_id}", response_model=Integration)
def get_integration(integration_id: UUID):
    rec = _integrations.get(integration_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Integration not found")
    return rec


# ─── Phase 10: Amazon Provider Status & Health ───────────────────────────────

@router.get("/integrations/amazon/capabilities")
def get_amazon_capabilities():
    """Return supported capabilities of the active Amazon provider."""
    provider = get_amazon_provider()
    return {
        "provider": getattr(provider, "provider_name", "unknown"),
        "capabilities": provider.check_capabilities(),
    }


@router.post("/integrations/amazon/test")
def test_amazon_integration():
    """Test connection and authentication to the configured Amazon provider."""
    provider = get_amazon_provider()
    return provider.test_connection()


# ─── Phase 11: Live Supplier Status & Health ──────────────────────────────────

@router.get("/integrations/suppliers/status")
def get_all_suppliers_status():
    """
    Return connection status, latency, and supported capabilities for all
    four supported supplier marketplaces (Home Depot, Walmart, Lowe's, AliExpress).
    """
    statuses = []
    for name, adapter_cls in ADAPTER_MAP.items():
        adapter = adapter_cls()
        test_res = adapter.test_connection()
        statuses.append({
            "supplier": name,
            "connected": test_res.get("connected", False),
            "status": test_res.get("status", "not_configured"),
            "message": test_res.get("message", ""),
            "capabilities": adapter.get_capabilities(),
        })
    return {"suppliers": statuses}


@router.post("/integrations/suppliers/{supplier}/test")
def test_supplier_integration(supplier: str):
    """Test connection for a specific supplier adapter."""
    adapter_cls = ADAPTER_MAP.get(supplier.lower())
    if not adapter_cls:
        raise HTTPException(404, f"Unknown supplier '{supplier}'. Supported: {list(ADAPTER_MAP.keys())}")
    adapter = adapter_cls()
    return adapter.test_connection()
