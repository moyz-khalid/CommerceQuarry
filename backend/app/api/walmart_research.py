"""
Walmart Seller Research API Router (Phase 2 & Phase 3).
Provides dedicated endpoints for:
  - Seller URL parsing and validation
  - Demo seller catalog discovery
  - CSV product catalog import
  - Provider capability and status inspection
  - Direct Walmart Seller Research scan launch
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.auth import get_current_user
from app.services.walmart import (
    parse_walmart_seller_url,
    get_walmart_provider,
    DEMO_SELLERS,
)
from app.services.sourcing.scan_store import create_scan, get_scan
from app.api.scans import _enqueue, _scan_to_response
from app.schemas.scan_schemas import ScanResponse

router = APIRouter(prefix="/walmart", tags=["Walmart Seller Research"])


# ─── Request / Response Models ────────────────────────────────────────────────

class ParseSellerUrlRequest(BaseModel):
    url_or_id: str = Field(..., description="Walmart seller storefront URL or Seller ID")


class ParseSellerUrlResponse(BaseModel):
    valid: bool
    seller_id: Optional[str] = None
    seller_name: Optional[str] = None
    storefront_url: str
    error: Optional[str] = None
    product_count: Optional[int] = None
    rating: Optional[float] = None
    is_demo: bool = False


class WalmartScanLaunchRequest(BaseModel):
    seller_id: Optional[str] = None
    storefront_url: Optional[str] = None
    provider: str = Field("demo", description="demo | serpapi | apify | csv")
    max_products: int = Field(50, ge=1, le=1000)
    suppliers: List[str] = Field(default_factory=lambda: ["home_depot", "lowes", "aliexpress"])
    fulfillment_methods: List[str] = Field(default_factory=lambda: ["walmart_wfs", "walmart_sf"])
    min_selling_price: Optional[float] = Field(None, ge=0)
    max_selling_price: Optional[float] = Field(None, ge=0)
    min_profit: Optional[float] = Field(None)
    min_roi: Optional[float] = Field(None)
    enable_ai_verification: bool = False
    use_cache: bool = True
    demo: bool = True
    csv_text: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/parse-seller-url", response_model=ParseSellerUrlResponse)
def parse_seller_url(req: ParseSellerUrlRequest):
    """
    Validates and extracts seller ID and storefront URL from a Walmart link or ID.
    Enriches with demo metadata if matching a known demo seller profile.
    """
    result = parse_walmart_seller_url(req.url_or_id)
    if not result["valid"]:
        return ParseSellerUrlResponse(
            valid=False,
            seller_id=None,
            seller_name=None,
            storefront_url=result.get("storefront_url", ""),
            error=result.get("error"),
            is_demo=False,
        )

    seller_id = result["seller_id"]
    seller_name = result["seller_name"]
    product_count = None
    rating = None
    is_demo = False

    # Check if known demo seller
    if seller_id in DEMO_SELLERS:
        demo_meta = DEMO_SELLERS[seller_id]
        seller_name = demo_meta["seller_name"]
        product_count = demo_meta["product_count"]
        rating = demo_meta["rating"]
        is_demo = True

    return ParseSellerUrlResponse(
        valid=True,
        seller_id=seller_id,
        seller_name=seller_name,
        storefront_url=result["storefront_url"],
        error=None,
        product_count=product_count,
        rating=rating,
        is_demo=is_demo,
    )


@router.get("/demo-sellers")
def list_demo_sellers():
    """Returns the list of realistic pre-configured Walmart demo seller profiles."""
    sellers = []
    for sid, data in DEMO_SELLERS.items():
        categories = list({p.get("category") for p in data["products"] if p.get("category")})
        sellers.append({
            "seller_id": data["seller_id"],
            "seller_name": data["seller_name"],
            "storefront_url": data["storefront_url"],
            "product_count": data["product_count"],
            "rating": data["rating"],
            "categories": categories,
            "sample_products": [p["product_title"] for p in data["products"][:3]],
            "is_demo": True,
        })
    return sellers


@router.get("/providers")
def list_walmart_providers():
    """Returns the registry of Walmart data providers and their operational status."""
    demo_p = get_walmart_provider("demo", demo=True)
    serpapi_p = get_walmart_provider("serpapi", demo=False)
    apify_p = get_walmart_provider("apify", demo=False)
    csv_p = get_walmart_provider("csv", demo=True)

    return {
        "providers": [
            {
                "id": "demo",
                "name": "Simulated Demo Catalog",
                "capabilities": demo_p.get_capabilities(),
            },
            {
                "id": "serpapi",
                "name": "SerpApi Walmart Search",
                "capabilities": serpapi_p.get_capabilities(),
            },
            {
                "id": "apify",
                "name": "Apify Walmart Scraper",
                "capabilities": apify_p.get_capabilities(),
            },
            {
                "id": "csv",
                "name": "CSV / Manual Import",
                "capabilities": csv_p.get_capabilities(),
            },
        ]
    }


@router.post("/upload-products-csv")
async def upload_products_csv(file: UploadFile = File(...)):
    """Upload and validate a CSV file containing Walmart products."""
    content = await file.read()
    try:
        csv_text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        csv_text = content.decode("latin-1")

    from app.services.walmart.csv_provider import CsvWalmartProvider
    provider = CsvWalmartProvider.from_csv_text(csv_text, seller_id="uploaded_csv")
    products, total = provider.get_seller_products("uploaded_csv", limit=500)

    if not products:
        raise HTTPException(400, "No valid product records found in the uploaded CSV.")

    return {
        "success": True,
        "filename": file.filename,
        "product_count": len(products),
        "sample": [p.to_dict() for p in products[:5]],
        "raw_csv_text": csv_text,
    }


@router.post("/seller-scan", response_model=ScanResponse, status_code=201)
def launch_walmart_seller_scan(
    req: WalmartScanLaunchRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    """
    Launches a dedicated Walmart Seller Research scan.
    Drives product retrieval, supplier multi-search, matching, and profitability calculation.
    """
    config = req.dict()
    config["mode"] = "walmart_seller"

    scan = create_scan(
        user_id=user_id,
        mode="walmart_seller",
        config=config,
        demo=req.demo,
    )

    background_tasks.add_task(_enqueue, scan.id)
    return _scan_to_response(scan)
