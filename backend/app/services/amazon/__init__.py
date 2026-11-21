"""
Amazon Provider Package (Phase 10).
"""
from app.services.amazon.base import AmazonProduct, AmazonProviderBase
from app.services.amazon.demo_adapter import DemoAmazonProvider
from app.services.amazon.rainforest_adapter import RainforestAmazonProvider
from app.services.amazon.factory import get_amazon_provider

__all__ = [
    "AmazonProduct",
    "AmazonProviderBase",
    "DemoAmazonProvider",
    "RainforestAmazonProvider",
    "get_amazon_provider",
]
