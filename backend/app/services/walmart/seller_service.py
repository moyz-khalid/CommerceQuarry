"""
Walmart Seller URL Parsing & Validation Service (Phase 2).
Handles robust extraction of seller IDs and names from varied Walmart storefront URLs.
"""
import re
import urllib.parse
from typing import Dict, Any, Optional


WALMART_SELLER_PATTERNS = [
    # 1. Standard seller storefront path: https://www.walmart.com/seller/101001234
    r"^https?:\/\/(?:www\.)?walmart\.com\/seller\/([a-zA-Z0-9_\-]+)",
    # 2. Browse by seller path: https://www.walmart.com/browse/seller/101001234
    r"^https?:\/\/(?:www\.)?walmart\.com\/browse\/seller\/([a-zA-Z0-9_\-]+)",
    # 3. Query param format: https://www.walmart.com/seller?sellerId=101001234
    r"[?&]sellerId=([a-zA-Z0-9_\-]+)",
    # 4. Search filtered by seller: https://www.walmart.com/search?facet=seller_id:101001234
    r"[?&]facet=seller_id:([a-zA-Z0-9_\-]+)",
]


def parse_walmart_seller_url(url_or_id: str) -> Dict[str, Any]:
    """
    Parses a Walmart seller URL or direct seller ID.
    Returns:
      {
        "valid": bool,
        "seller_id": Optional[str],
        "seller_name": Optional[str],
        "storefront_url": str,
        "error": Optional[str],
      }
    """
    if not url_or_id or not url_or_id.strip():
        return {
            "valid": False,
            "seller_id": None,
            "seller_name": None,
            "storefront_url": "",
            "error": "Storefront URL or Seller ID cannot be empty.",
        }

    raw = url_or_id.strip()

    # Case A: User entered a direct seller ID (e.g. "101001", "F7B943A")
    if re.match(r"^[a-zA-Z0-9_\-]{3,32}$", raw):
        seller_id = raw
        canonical_url = f"https://www.walmart.com/seller/{seller_id}"
        return {
            "valid": True,
            "seller_id": seller_id,
            "seller_name": f"Walmart Seller {seller_id}",
            "storefront_url": canonical_url,
            "error": None,
        }

    # Case B: User entered a full URL
    try:
        parsed = urllib.parse.urlparse(raw)
        if not parsed.scheme or not parsed.netloc:
            # Try prepending https://
            parsed = urllib.parse.urlparse("https://" + raw)
    except Exception as e:
        return {
            "valid": False,
            "seller_id": None,
            "seller_name": None,
            "storefront_url": raw,
            "error": f"Invalid URL structure: {str(e)}",
        }

    # Validate domain
    if "walmart.com" not in parsed.netloc.lower():
        return {
            "valid": False,
            "seller_id": None,
            "seller_name": None,
            "storefront_url": raw,
            "error": "URL domain must be walmart.com (e.g. https://www.walmart.com/seller/101001).",
        }

    # Match seller ID from URL patterns
    for pattern in WALMART_SELLER_PATTERNS:
        m = re.search(pattern, raw, re.IGNORECASE)
        if m:
            seller_id = m.group(1)
            # Filter out non-seller words that might match
            if seller_id.lower() in {"search", "browse", "ip", "help", "account"}:
                continue
            canonical_url = f"https://www.walmart.com/seller/{seller_id}"
            return {
                "valid": True,
                "seller_id": seller_id,
                "seller_name": f"Walmart Seller {seller_id}",
                "storefront_url": canonical_url,
                "error": None,
            }

    # Fallback: check query parameters directly
    try:
        qs = urllib.parse.parse_qs(parsed.query)
        for key in ["sellerId", "seller_id", "seller"]:
            if key in qs and qs[key]:
                seller_id = qs[key][0]
                return {
                    "valid": True,
                    "seller_id": seller_id,
                    "seller_name": f"Walmart Seller {seller_id}",
                    "storefront_url": f"https://www.walmart.com/seller/{seller_id}",
                    "error": None,
                }
    except Exception:
        pass

    return {
        "valid": False,
        "seller_id": None,
        "seller_name": None,
        "storefront_url": raw,
        "error": "Could not extract a valid Walmart Seller ID from the provided URL. Expected format: https://www.walmart.com/seller/{seller_id} or enter the Seller ID directly.",
    }
