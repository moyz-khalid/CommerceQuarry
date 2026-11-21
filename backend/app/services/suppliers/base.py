"""
Supplier Adapter Base Architecture (Phase 11).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class SupplierCandidate:
    supplier_name: str
    supplier_product_id: str
    title: str
    price: float
    url: str
    image_url: Optional[str] = None
    upc: Optional[str] = None
    mpn: Optional[str] = None
    model_number: Optional[str] = None
    brand: Optional[str] = None
    pack_count: int = 1
    in_stock: bool = True
    shipping_cost: float = 0.0
    retrieved_at: Optional[str] = None
    source: str = "supplier_adapter"
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("raw_data", None)
        d["supplier_title"] = self.title
        d["supplier_price"] = self.price
        d["supplier_url"] = self.url
        d["package_quantity"] = self.pack_count
        return d


class SupplierAdapterBase(ABC):
    """Abstract interface that each marketplace adapter must implement."""

    @abstractmethod
    def get_supplier_name(self) -> str:
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        upc: Optional[str] = None,
        mpn: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 5,
    ) -> List[SupplierCandidate]:
        """Search products using query text or exact identifiers."""
        pass

    @abstractmethod
    def get_product_detail(self, product_id_or_url: str) -> Optional[SupplierCandidate]:
        """Fetch real-time product detail, price, and stock status."""
        pass

    @abstractmethod
    def get_capabilities(self) -> Dict[str, bool]:
        """Return dict of capabilities supported by this supplier adapter."""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Test authentication and health of the supplier adapter."""
        pass
