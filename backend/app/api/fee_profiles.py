"""
Fee Profiles API Router (Phase 7).

Provides complete CRUD, duplication, and fulfillment method rules for user fee profiles.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict
from app.auth import get_current_user

router = APIRouter()

# ─── Schemas ──────────────────────────────────────────────────────────────────

SUPPORTED_METHODS = ["amazon_fba", "amazon_fbm", "walmart_wfs", "walmart_sf"]


class FeeProfileBase(BaseModel):
    name: str = Field(..., description="Profile name")
    description: Optional[str] = None
    fulfillment_method: str = Field("amazon_fba", description="amazon_fba | amazon_fbm | walmart_wfs | walmart_sf")
    is_default: bool = False
    is_enabled: bool = True
    # Fee and cost rules
    referral_fee_pct: float = Field(15.0, ge=0, le=100)
    fulfillment_fee_flat: float = Field(3.50, ge=0)
    inbound_shipping_per_lb: float = Field(0.45, ge=0)
    prep_cost_per_unit: float = Field(1.00, ge=0)
    packaging_cost_per_unit: float = Field(0.50, ge=0)
    storage_fee_monthly_per_cuft: float = Field(0.87, ge=0)
    handling_per_order: float = Field(0.25, ge=0)
    misc_overhead_flat: float = Field(0.25, ge=0)


class FeeProfileCreate(FeeProfileBase):
    pass


class FeeProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    fulfillment_method: Optional[str] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None
    referral_fee_pct: Optional[float] = None
    fulfillment_fee_flat: Optional[float] = None
    inbound_shipping_per_lb: Optional[float] = None
    prep_cost_per_unit: Optional[float] = None
    packaging_cost_per_unit: Optional[float] = None
    storage_fee_monthly_per_cuft: Optional[float] = None
    handling_per_order: Optional[float] = None
    misc_overhead_flat: Optional[float] = None


class FeeProfileResponse(FeeProfileBase):
    id: UUID
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


# ─── In-memory Profile Store ─────────────────────────────────────────────────

_profiles_store: Dict[UUID, dict] = {}


def _seed_defaults(user_id: str):
    """Seed initial standard profiles for user if missing."""
    existing_methods = {p["fulfillment_method"] for p in _profiles_store.values() if p["user_id"] == user_id}
    defaults = [
        {
            "name": "Amazon FBA Standard",
            "description": "Standard Amazon FBA inbound & fulfillment fees",
            "fulfillment_method": "amazon_fba",
            "is_default": True,
            "is_enabled": True,
            "referral_fee_pct": 15.0,
            "fulfillment_fee_flat": 3.22,
            "inbound_shipping_per_lb": 0.45,
            "prep_cost_per_unit": 1.00,
            "packaging_cost_per_unit": 0.50,
            "storage_fee_monthly_per_cuft": 0.87,
            "handling_per_order": 0.0,
            "misc_overhead_flat": 0.25,
        },
        {
            "name": "Amazon FBM My Warehouse",
            "description": "Seller-fulfilled Amazon orders shipped via UPS/USPS",
            "fulfillment_method": "amazon_fbm",
            "is_default": True,
            "is_enabled": True,
            "referral_fee_pct": 15.0,
            "fulfillment_fee_flat": 0.0,
            "inbound_shipping_per_lb": 0.0,
            "prep_cost_per_unit": 0.50,
            "packaging_cost_per_unit": 0.85,
            "storage_fee_monthly_per_cuft": 0.0,
            "handling_per_order": 1.50,
            "misc_overhead_flat": 0.25,
        },
        {
            "name": "Walmart WFS Standard",
            "description": "Walmart Fulfillment Services standard rates",
            "fulfillment_method": "walmart_wfs",
            "is_default": True,
            "is_enabled": True,
            "referral_fee_pct": 15.0,
            "fulfillment_fee_flat": 3.45,
            "inbound_shipping_per_lb": 0.40,
            "prep_cost_per_unit": 0.90,
            "packaging_cost_per_unit": 0.40,
            "storage_fee_monthly_per_cuft": 0.75,
            "handling_per_order": 0.0,
            "misc_overhead_flat": 0.25,
        },
        {
            "name": "Walmart Seller-Fulfilled",
            "description": "Walmart marketplace orders fulfilled from merchant hub",
            "fulfillment_method": "walmart_sf",
            "is_default": True,
            "is_enabled": True,
            "referral_fee_pct": 15.0,
            "fulfillment_fee_flat": 0.0,
            "inbound_shipping_per_lb": 0.0,
            "prep_cost_per_unit": 0.50,
            "packaging_cost_per_unit": 0.85,
            "storage_fee_monthly_per_cuft": 0.0,
            "handling_per_order": 1.50,
            "misc_overhead_flat": 0.25,
        },
    ]
    for d in defaults:
        if d["fulfillment_method"] not in existing_methods:
            p_id = uuid4()
            _profiles_store[p_id] = {
                "id": p_id,
                "user_id": user_id,
                **d,
                "created_at": datetime.utcnow(),
                "updated_at": None,
            }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/fee-profiles", response_model=List[FeeProfileResponse])
def list_fee_profiles(user_id: str = Depends(get_current_user)):
    """List all fee profiles belonging to current user."""
    _seed_defaults(user_id)
    return [p for p in _profiles_store.values() if p["user_id"] == user_id]


@router.post("/fee-profiles", response_model=FeeProfileResponse, status_code=status.HTTP_201_CREATED)
def create_fee_profile(req: FeeProfileCreate, user_id: str = Depends(get_current_user)):
    """Create a new fee profile."""
    if req.fulfillment_method not in SUPPORTED_METHODS:
        raise HTTPException(400, f"fulfillment_method must be one of {SUPPORTED_METHODS}")

    p_id = uuid4()
    # If set as default, unset other defaults for same method
    if req.is_default:
        for p in _profiles_store.values():
            if p["user_id"] == user_id and p["fulfillment_method"] == req.fulfillment_method:
                p["is_default"] = False

    data = {
        "id": p_id,
        "user_id": user_id,
        **req.dict(),
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }
    _profiles_store[p_id] = data
    return data


@router.get("/fee-profiles/{profile_id}", response_model=FeeProfileResponse)
def get_fee_profile(profile_id: UUID, user_id: str = Depends(get_current_user)):
    """Get fee profile details."""
    p = _profiles_store.get(profile_id)
    if not p:
        raise HTTPException(404, "Fee profile not found")
    if p["user_id"] != user_id:
        raise HTTPException(403, "Forbidden")
    return p


@router.put("/fee-profiles/{profile_id}", response_model=FeeProfileResponse)
def update_fee_profile(
    profile_id: UUID,
    req: FeeProfileUpdate,
    user_id: str = Depends(get_current_user),
):
    """Update an existing fee profile."""
    p = _profiles_store.get(profile_id)
    if not p:
        raise HTTPException(404, "Fee profile not found")
    if p["user_id"] != user_id:
        raise HTTPException(403, "Forbidden")

    updates = {k: v for k, v in req.dict(exclude_unset=True).items()}
    if "is_default" in updates and updates["is_default"]:
        method = updates.get("fulfillment_method", p["fulfillment_method"])
        for other in _profiles_store.values():
            if other["user_id"] == user_id and other["fulfillment_method"] == method:
                other["is_default"] = False

    for k, v in updates.items():
        p[k] = v
    p["updated_at"] = datetime.utcnow()
    return p


@router.delete("/fee-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fee_profile(profile_id: UUID, user_id: str = Depends(get_current_user)):
    """Delete a fee profile."""
    p = _profiles_store.get(profile_id)
    if not p:
        raise HTTPException(404, "Fee profile not found")
    if p["user_id"] != user_id:
        raise HTTPException(403, "Forbidden")
    del _profiles_store[profile_id]
    return None


@router.post("/fee-profiles/{profile_id}/duplicate", response_model=FeeProfileResponse, status_code=status.HTTP_201_CREATED)
def duplicate_fee_profile(profile_id: UUID, user_id: str = Depends(get_current_user)):
    """Duplicate an existing fee profile."""
    p = _profiles_store.get(profile_id)
    if not p:
        raise HTTPException(404, "Fee profile not found")
    if p["user_id"] != user_id:
        raise HTTPException(403, "Forbidden")

    new_id = uuid4()
    copy_data = dict(p)
    copy_data["id"] = new_id
    copy_data["name"] = f"{p['name']} (Copy)"
    copy_data["is_default"] = False
    copy_data["created_at"] = datetime.utcnow()
    copy_data["updated_at"] = None

    _profiles_store[new_id] = copy_data
    return copy_data


@router.post("/fee-profiles/{profile_id}/set-default", response_model=FeeProfileResponse)
def set_profile_as_default(profile_id: UUID, user_id: str = Depends(get_current_user)):
    """Set profile as default for its fulfillment method."""
    p = _profiles_store.get(profile_id)
    if not p:
        raise HTTPException(404, "Fee profile not found")
    if p["user_id"] != user_id:
        raise HTTPException(403, "Forbidden")

    method = p["fulfillment_method"]
    for other in _profiles_store.values():
        if other["user_id"] == user_id and other["fulfillment_method"] == method:
            other["is_default"] = (other["id"] == profile_id)

    p["updated_at"] = datetime.utcnow()
    return p
