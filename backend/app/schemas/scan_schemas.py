"""
Scan schemas: request/response models for the scan API.
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import re

# ─── Enum constants ────────────────────────────────────────────────────────────

SCAN_MODES = {"category", "seller", "product", "walmart_seller"}

SCAN_STATUSES = {
    "queued",
    "running",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
}

SUPPORTED_SUPPLIERS = ["home_depot", "walmart", "lowes", "aliexpress"]

FULFILLMENT_METHODS = ["amazon_fba", "amazon_fbm", "walmart_wfs", "walmart_sf"]

AMAZON_CATEGORIES = [
    "Home & Kitchen",
    "Tools & Home Improvement",
    "Sports & Outdoors",
    "Beauty & Personal Care",
    "Pet Supplies",
    "Electronics",
    "Toys & Games",
    "Office Products",
    "Garden & Outdoor",
    "Automotive",
]

# ─── Category sourcing config ──────────────────────────────────────────────────

class CategorySourcingConfig(BaseModel):
    category: str = Field(..., description="Amazon category name")
    amazon_price_min: Optional[float] = Field(None, ge=0)
    amazon_price_max: Optional[float] = Field(None, ge=0)
    supplier_price_min: Optional[float] = Field(None, ge=0)
    supplier_price_max: Optional[float] = Field(None, ge=0)
    min_profit: Optional[float] = Field(None)
    min_roi: Optional[float] = Field(None)
    min_margin: Optional[float] = Field(None)
    max_products: int = Field(100, ge=1, le=1000)
    suppliers: List[str] = Field(default_factory=lambda: SUPPORTED_SUPPLIERS)
    fulfillment_methods: List[str] = Field(default_factory=lambda: FULFILLMENT_METHODS)
    demo: bool = False

    @validator("category")
    def validate_category(cls, v):
        if v not in AMAZON_CATEGORIES:
            raise ValueError(f"Category '{v}' is not in the supported category list.")
        return v

    @validator("suppliers", each_item=True)
    def validate_supplier(cls, v):
        if v not in SUPPORTED_SUPPLIERS:
            raise ValueError(f"Supplier '{v}' is not supported.")
        return v

    @validator("fulfillment_methods", each_item=True)
    def validate_fulfillment(cls, v):
        if v not in FULFILLMENT_METHODS:
            raise ValueError(f"Fulfillment method '{v}' is not supported.")
        return v


# ─── Seller sourcing config ───────────────────────────────────────────────────

class SellerSourcingConfig(BaseModel):
    seller_id: Optional[str] = Field(None)
    storefront_url: Optional[str] = Field(None)
    max_products: int = Field(100, ge=1, le=1000)
    suppliers: List[str] = Field(default_factory=lambda: SUPPORTED_SUPPLIERS)
    fulfillment_methods: List[str] = Field(default_factory=lambda: FULFILLMENT_METHODS)
    demo: bool = False

    @validator("storefront_url", always=True)
    def validate_at_least_one(cls, v, values):
        seller_id = values.get("seller_id")
        if not seller_id and not v:
            raise ValueError("Either seller_id or storefront_url must be provided.")
        return v

    @validator("storefront_url")
    def validate_url(cls, v):
        if v and not (
            v.startswith("https://www.amazon.")
            or v.startswith("https://www.walmart.")
            or v.startswith("http://")
            or v.startswith("https://")
        ):
            raise ValueError("storefront_url must be a valid URL (amazon.com, walmart.com, or any https URL).")
        return v


# ─── Product (ASIN) sourcing config ───────────────────────────────────────────

ASIN_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
AMAZON_URL_PATTERN = re.compile(r"amazon\.[a-z.]+/(dp|gp/product)/([A-Z0-9]{10})")

class ProductSourcingConfig(BaseModel):
    asin: Optional[str] = Field(None)
    product_url: Optional[str] = Field(None)
    suppliers: List[str] = Field(default_factory=lambda: SUPPORTED_SUPPLIERS)
    fulfillment_methods: List[str] = Field(default_factory=lambda: FULFILLMENT_METHODS)
    demo: bool = False

    @validator("asin")
    def validate_asin(cls, v):
        if v and not ASIN_PATTERN.match(v):
            raise ValueError("ASIN must be a 10-character alphanumeric string.")
        return v

    @validator("product_url", always=True)
    def validate_product_url_or_asin(cls, v, values):
        asin = values.get("asin")
        if not asin and not v:
            raise ValueError("Either asin or product_url must be provided.")
        if v:
            m = AMAZON_URL_PATTERN.search(v)
            if not m:
                raise ValueError("product_url must be a valid Amazon product URL containing a 10-char ASIN.")
        return v

    def resolved_asin(self) -> str:
        """Return the ASIN whether supplied directly or extracted from URL."""
        if self.asin:
            return self.asin
        m = AMAZON_URL_PATTERN.search(self.product_url)
        return m.group(2) if m else ""


# ─── Walmart Seller Research config ───────────────────────────────────────────

class WalmartSellerResearchConfig(BaseModel):
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


# ─── Generic scan create request ─────────────────────────────────────────────

class ScanCreateRequest(BaseModel):
    mode: Optional[str] = Field(default="category", description="category | seller | product | walmart_seller")
    config: Optional[dict] = None
    category_config: Optional[CategorySourcingConfig] = None
    seller_config: Optional[SellerSourcingConfig] = None
    product_config: Optional[ProductSourcingConfig] = None
    walmart_seller_config: Optional[WalmartSellerResearchConfig] = None
    demo: bool = False

    @root_validator(pre=True)
    def handle_legacy_config(cls, values):
        if isinstance(values, dict):
            if "mode" not in values and "config" in values:
                cfg = values.get("config") or {}
                if isinstance(cfg, dict) and "mode" in cfg:
                    values["mode"] = cfg["mode"]
            if not values.get("mode"):
                values["mode"] = "category"
        return values

    @validator("mode")
    def validate_mode(cls, v):
        if v not in SCAN_MODES:
            raise ValueError(f"mode must be one of {SCAN_MODES}")
        return v


# ─── Scan response ────────────────────────────────────────────────────────────

class ScanResponse(BaseModel):
    id: UUID
    user_id: str
    mode: str
    status: str
    progress: int = 0
    total: int = 0
    matched: int = 0
    profitable: int = 0
    error_summary: Optional[str] = None
    demo: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ScanProgressResponse(BaseModel):
    id: UUID
    status: str
    progress: int
    total: int
    matched: int
    profitable: int
    error_summary: Optional[str] = None


# ─── Phase 4 & 5: Results & Matching schemas ──────────────────────────────────

class MatchInfo(BaseModel):
    matched: bool
    confidence: str                  # "exact" | "high" | "medium" | "low" | "none"
    score: float
    match_method: str                # "upc" | "mpn" | "title" | "demo_stub" | "none"
    mismatch_reason: Optional[str] = None
    deterministic_score: Optional[float] = None
    confidence_band: Optional[str] = None   # "strong_match" | "likely_match" | "manual_review" | "rejected"
    match_type: Optional[str] = None
    explanation: Optional[str] = None
    differences: List[str] = Field(default_factory=list)
    manual_review: bool = False
    final_decision: str = "accepted"        # "accepted" | "review" | "rejected"
    reviewer_decision: Optional[str] = None # "accepted" | "rejected"
    reviewer_notes: Optional[str] = None
    engine_version: Optional[str] = None
    # Phase 6: DeepSeek AI Verification
    ai_verified: bool = False
    ai_score: Optional[float] = None
    ai_decision: Optional[str] = None
    ai_reason: Optional[str] = None
    ai_differences: List[str] = Field(default_factory=list)
    tokens_used: Optional[int] = None
    ai_cost_usd: Optional[float] = None


class MatchReviewRequest(BaseModel):
    decision: str = Field(..., description="accepted | rejected | investigation")
    notes: Optional[str] = None
    corrected_price: Optional[float] = None
    corrected_pack_count: Optional[int] = None

    @validator("decision")
    def validate_decision(cls, v):
        if v not in ("accepted", "rejected", "investigation"):
            raise ValueError("decision must be 'accepted', 'rejected', or 'investigation'")
        return v


class ProfitInfo(BaseModel):
    profitable: bool
    net_profit: float
    roi_pct: float
    margin_pct: float
    referral_fee: float
    fba_fee: float
    total_fees: float
    total_cost: float
    break_even_price: float
    total_profit: float
    supplier_cost: Optional[float] = None
    simulated: Optional[bool] = None
    # Phase 7: Multi-Method Fulfillment & Calculation Status
    best_fulfillment_method: Optional[str] = "amazon_fba"
    calculation_status: Optional[str] = "verified" # "verified" | "estimated" | "incomplete"
    fulfillment_breakdown: Optional[dict] = None
    itemized_expenses: Optional[dict] = None


class ScanResultItem(BaseModel):
    asin: str
    title: str
    brand: Optional[str] = None
    amazon_price: float
    url: Optional[str] = None
    image_url: Optional[str] = None
    upc: Optional[str] = None
    mpn: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_title: Optional[str] = None
    supplier_url: Optional[str] = None
    supplier_image_url: Optional[str] = None
    simulated: bool = False
    starred: bool = False
    match: MatchInfo
    profit: ProfitInfo
    audit_trail: List[dict] = Field(default_factory=list)
    corrected_price: Optional[float] = None
    corrected_pack_count: Optional[int] = None


class ScanResultsResponse(BaseModel):
    scan_id: UUID
    status: str
    total_results: int
    matched_count: int
    profitable_count: int
    review_count: int = 0
    results: List[ScanResultItem]
