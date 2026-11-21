"""
Suppliers package (Phase 5 & 11).
"""
from app.services.suppliers.base import SupplierCandidate, SupplierAdapterBase
from app.services.suppliers.homedepot_adapter import HomeDepotAdapter
from app.services.suppliers.walmart_adapter import WalmartAdapter
from app.services.suppliers.lowes_adapter import LowesAdapter
from app.services.suppliers.aliexpress_adapter import AliExpressAdapter
from app.services.suppliers.multi_search import execute_multi_supplier_search, ADAPTER_MAP
from app.services.suppliers.discovery import normalize_supplier_product, search_supplier_candidates, SUPPORTED_SUPPLIERS

__all__ = [
    "SupplierCandidate",
    "SupplierAdapterBase",
    "HomeDepotAdapter",
    "WalmartAdapter",
    "LowesAdapter",
    "AliExpressAdapter",
    "execute_multi_supplier_search",
    "ADAPTER_MAP",
    "normalize_supplier_product",
    "search_supplier_candidates",
    "SUPPORTED_SUPPLIERS",
]
