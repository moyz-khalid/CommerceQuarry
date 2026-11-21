"""
Amazon Provider Factory (Phase 10).
"""
import os
from typing import Optional
from app.services.amazon.base import AmazonProviderBase
from app.services.amazon.demo_adapter import DemoAmazonProvider
from app.services.amazon.rainforest_adapter import RainforestAmazonProvider


def get_amazon_provider(provider_type: Optional[str] = None) -> AmazonProviderBase:
    """
    Factory to return the configured Amazon provider instance.
    Defaults to 'demo' if no live API key is set or if provider_type='demo'.
    """
    selected = provider_type or os.getenv("AMAZON_PROVIDER", "demo").lower()

    if selected == "rainforest" and os.getenv("RAINFOREST_API_KEY"):
        return RainforestAmazonProvider()
    elif selected == "rainforest":
        return RainforestAmazonProvider()  # Will report not_configured in test_connection
    else:
        return DemoAmazonProvider()
