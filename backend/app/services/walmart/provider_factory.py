"""
Walmart Provider Factory (Phase 3).
Instantiates the configured Walmart data provider.
Defaults to the realistic DemoWalmartProvider when live keys are absent.
Rainforest is never required.
"""
import os
from typing import Optional
from app.services.walmart.base import WalmartProviderBase
from app.services.walmart.demo_provider import DemoWalmartProvider
from app.services.walmart.csv_provider import CsvWalmartProvider
from app.services.walmart.serpapi_provider import SerpApiWalmartProvider
from app.services.walmart.apify_provider import ApifyWalmartProvider


def get_walmart_provider(
    provider_type: Optional[str] = None,
    demo: bool = True,
    csv_text: Optional[str] = None,
) -> WalmartProviderBase:
    """
    Factory to return the selected Walmart data provider instance.
    If demo=True or no live credentials configured, safely returns DemoWalmartProvider.
    """
    if csv_text:
        return CsvWalmartProvider.from_csv_text(csv_text)

    selected = (provider_type or os.getenv("WALMART_PROVIDER", "demo")).lower().strip()

    if selected == "csv":
        return CsvWalmartProvider()

    if not demo:
        if selected in ("serpapi", "serpapi_walmart") and os.getenv("SERPAPI_API_KEY"):
            return SerpApiWalmartProvider()
        elif selected in ("apify", "apify_walmart") and os.getenv("APIFY_TOKEN"):
            return ApifyWalmartProvider()

    # Default: Always provide robust, zero-crash simulated catalog
    return DemoWalmartProvider()
