"""
Walmart Data Provider Interfaces and Schemas (Phase 3 & Phase 4).
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from abc import ABC, abstractmethod


@dataclass
class WalmartProduct:
    """Normalized Walmart product model complying with Phase 4 specifications."""
    product_title: str
    walmart_product_id: str
    product_url: str
    image_url: Optional[str] = None
    current_price: float = 0.0
    original_price: Optional[float] = None
    currency: str = "USD"
    brand: Optional[str] = None
    upc: Optional[str] = None
    gtin: Optional[str] = None
    model_number: Optional[str] = None
    mpn: Optional[str] = None
    description: Optional[str] = None
    specifications: Dict[str, Any] = field(default_factory=dict)
    dimensions: Optional[str] = None
    weight_lbs: Optional[float] = None
    package_quantity: int = 1
    category: Optional[str] = None
    availability: str = "in_stock"
    seller_id: Optional[str] = None
    seller_name: Optional[str] = None
    provider_name: str = "unknown"
    collected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data_freshness: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_demo: bool = False
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Compatibility aliases for shared matching and sourcing pipeline
        d["title"] = self.product_title
        d["price"] = self.current_price
        d["walmart_price"] = self.current_price
        d["url"] = self.product_url
        d["asin"] = self.walmart_product_id  # Primary key alias for results table
        d["sku"] = self.walmart_product_id
        return d


@dataclass
class WalmartSellerInfo:
    """Information identifying a Walmart marketplace seller."""
    seller_id: str
    seller_name: str
    storefront_url: str
    product_count: Optional[int] = None
    rating: Optional[float] = None
    is_verified: bool = True
    provider: str = "unknown"
    is_demo: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WalmartProviderBase(ABC):
    """Abstract Base Class for Walmart data providers."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider identifier (e.g. 'demo', 'serpapi', 'apify', 'csv')."""
        pass

    @abstractmethod
    def identify_seller(self, url_or_id: str) -> Optional[WalmartSellerInfo]:
        """Resolve seller details from a storefront URL or seller ID."""
        pass

    @abstractmethod
    def get_seller_products(
        self,
        seller_id: str,
        limit: int = 50,
        page: int = 1,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> Tuple[List[WalmartProduct], Optional[int]]:
        """
        Retrieve a page of products for a seller.
        Returns: (list_of_normalized_products, total_available_count)
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities, configuration status, and limitations."""
        pass
