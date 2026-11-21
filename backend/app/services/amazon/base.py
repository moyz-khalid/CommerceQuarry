"""
Amazon Product & Provider Base Architecture (Phase 10).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

AMAZON_URL_PATTERN = re.compile(r"amazon\.[a-z\.]+/dp/([A-Z0-9]{10})|amazon\.[a-z\.]+/gp/product/([A-Z0-9]{10})", re.IGNORECASE)


@dataclass
class AmazonProduct:
    asin: str
    title: str
    brand: Optional[str] = None
    price: float = 0.0
    url: Optional[str] = None
    image_url: Optional[str] = None
    upc: Optional[str] = None
    mpn: Optional[str] = None
    model_number: Optional[str] = None
    weight_lbs: Optional[float] = None
    dimensions: Optional[str] = None
    category: Optional[str] = None
    in_stock: bool = True
    rating: Optional[float] = None
    review_count: Optional[int] = None
    source: str = "amazon"
    retrieved_at: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("raw_data", None)
        d["amazon_price"] = self.price
        return d


class AmazonProviderBase(ABC):
    """Abstract base class for all Amazon product data providers."""

    @abstractmethod
    def lookup_asin(self, asin: str) -> Optional[AmazonProduct]:
        """Look up a single product by ASIN."""
        pass

    @abstractmethod
    def lookup_url(self, url: str) -> Optional[AmazonProduct]:
        """Look up a product from an Amazon URL."""
        pass

    @abstractmethod
    def discover_category(
        self,
        category: str,
        max_products: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[AmazonProduct]:
        """Discover products in an Amazon category."""
        pass

    @abstractmethod
    def get_seller_inventory(
        self,
        seller_id: str,
        max_products: int = 10,
    ) -> List[AmazonProduct]:
        """Retrieve products from an Amazon seller storefront."""
        pass

    @abstractmethod
    def check_capabilities(self) -> Dict[str, bool]:
        """Return dict of capabilities supported by this provider."""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test authentication and health of the provider API."""
        pass
