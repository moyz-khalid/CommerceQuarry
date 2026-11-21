"""
Demo provider — returns realistic Amazon and supplier records
so the full sourcing, matching, profitability, and export pipeline
can be exercised end-to-end without external API credentials.

Phase 4 dataset includes:
  - 6 Amazon categories
  - 4 supplier marketplaces (Home Depot, Walmart, Lowe's, AliExpress)
  - Realistic product specifications (UPC, MPN, dimensions, weight, pack count)
  - Realistic matching scenarios (exact match, high similarity, pack count conflict, model mismatch, unrelated item)
"""
from typing import List, Dict, Any, Optional

# ─── Rich Demo Amazon Products with Supplier Equivalents ──────────────────────

_DEMO_PRODUCTS: Dict[str, List[Dict[str, Any]]] = {
    "Home & Kitchen": [
        {
            "asin": "B08XYZ1001",
            "title": "Cuisinart 12-Cup Programmable Coffee Maker, Stainless Steel",
            "brand": "Cuisinart",
            "price": 49.99,
            "url": "https://www.amazon.com/dp/B08XYZ1001",
            "upc": "086279116918",
            "mpn": "DCC-1200",
            "model": "DCC-1200",
            "dimensions": "9.0 x 7.7 x 14.0 in",
            "weight_lbs": 6.8,
            "color": "Stainless Steel",
            "package_quantity": 1,
            "matched": True,
            "profitable": True,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "Walmart",
                    "supplier_title": "Cuisinart 12-Cup Programmable Coffee Maker, Stainless Steel DCC-1200",
                    "supplier_price": 28.50,
                    "supplier_url": "https://www.walmart.com/ip/Cuisinart-DCC-1200/1001",
                    "upc": "086279116918",
                    "mpn": "DCC-1200",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
        {
            "asin": "B07XYZ1002",
            "title": "AmazonBasics Microwave, Small, 0.7 Cu. Ft., 700W",
            "brand": "AmazonBasics",
            "price": 59.99,
            "url": "https://www.amazon.com/dp/B07XYZ1002",
            "upc": "",
            "mpn": "AGB34MD07",
            "model": "AGB34MD07",
            "dimensions": "17.3 x 10.1 x 14.1 in",
            "weight_lbs": 21.0,
            "color": "Black",
            "package_quantity": 1,
            "matched": False,
            "profitable": False,
            "simulated": True,
            "mismatch_reason": "No meaningful overlap",
            "supplier_candidates": [
                {
                    "supplier_name": "Home Depot",
                    "supplier_title": "Magic Chef 0.7 cu. ft. Countertop Microwave",
                    "supplier_price": 64.00,
                    "supplier_url": "https://www.homedepot.com/p/Magic-Chef-Microwave/1002",
                    "upc": "665679001234",
                    "mpn": "MCM770B",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
        {
            "asin": "B08XYZ1003",
            "title": "Brita Standard Water Filter Replacement, 3-Pack",
            "brand": "Brita",
            "price": 19.99,
            "url": "https://www.amazon.com/dp/B08XYZ1003",
            "upc": "060258362438",
            "mpn": "OB03",
            "model": "OB03",
            "dimensions": "4.2 x 4.2 x 9.5 in",
            "weight_lbs": 0.9,
            "color": "White",
            "package_quantity": 3,
            "matched": False,
            "profitable": False,
            "simulated": True,
            "mismatch_reason": "Pack count discrepancy: Amazon is 3-pack vs Supplier is 1-pack",
            "supplier_candidates": [
                {
                    "supplier_name": "Walmart",
                    "supplier_title": "Brita Standard Water Filter Replacement, Single Filter",
                    "supplier_price": 7.99,
                    "supplier_url": "https://www.walmart.com/ip/Brita-Filter/1003",
                    "upc": "060258362414",
                    "mpn": "OB01",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
    ],
    "Tools & Home Improvement": [
        {
            "asin": "B09XYZ2001",
            "title": "DEWALT 20V MAX Cordless Drill Combo Kit, 2-Tool",
            "brand": "DEWALT",
            "price": 139.00,
            "url": "https://www.amazon.com/dp/B09XYZ2001",
            "upc": "028877514573",
            "mpn": "DCK240C2",
            "model": "DCK240C2",
            "dimensions": "15.1 x 6.4 x 9.9 in",
            "weight_lbs": 9.1,
            "color": "Yellow/Black",
            "package_quantity": 1,
            "matched": True,
            "profitable": True,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "Home Depot",
                    "supplier_title": "DEWALT 20V MAX Cordless Compact Drill/Impact Combo Kit (2-Tool)",
                    "supplier_price": 89.00,
                    "supplier_url": "https://www.homedepot.com/p/DEWALT-DCK240C2/2001",
                    "upc": "028877514573",
                    "mpn": "DCK240C2",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
        {
            "asin": "B08XYZ2002",
            "title": "Stanley FatMax 25 ft Tape Measure, High Impact ABS",
            "brand": "Stanley",
            "price": 19.97,
            "url": "https://www.amazon.com/dp/B08XYZ2002",
            "upc": "076174330591",
            "mpn": "FMHT33865S",
            "model": "FMHT33865S",
            "dimensions": "3.5 x 2.2 x 5.8 in",
            "weight_lbs": 1.1,
            "color": "Black/Yellow",
            "package_quantity": 1,
            "matched": True,
            "profitable": False,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "Lowe's",
                    "supplier_title": "Stanley FatMax 25-ft Tape Measure FMHT33865S",
                    "supplier_price": 14.98,
                    "supplier_url": "https://www.lowes.com/pd/Stanley-FatMax/2002",
                    "upc": "076174330591",
                    "mpn": "FMHT33865S",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
    ],
    "Sports & Outdoors": [
        {
            "asin": "B07XYZ3001",
            "title": "Hydro Flask 32 oz Water Bottle Wide Mouth with Straw Lid",
            "brand": "Hydro Flask",
            "price": 44.95,
            "url": "https://www.amazon.com/dp/B07XYZ3001",
            "upc": "810497025139",
            "mpn": "W32BTS015",
            "model": "W32BTS015",
            "dimensions": "3.58 x 3.58 x 9.4 in",
            "weight_lbs": 0.95,
            "color": "Cobalt Blue",
            "package_quantity": 1,
            "matched": True,
            "profitable": True,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "Walmart",
                    "supplier_title": "Hydro Flask 32 oz Wide Mouth Stainless Steel Bottle Cobalt",
                    "supplier_price": 22.50,
                    "supplier_url": "https://www.walmart.com/ip/Hydro-Flask-32oz/3001",
                    "upc": "810497025139",
                    "mpn": "W32BTS015",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
    ],
    "Beauty & Personal Care": [
        {
            "asin": "B08XYZ4001",
            "title": "Neutrogena Hydro Boost Water Gel Face Moisturizer, 1.7 oz",
            "brand": "Neutrogena",
            "price": 18.97,
            "url": "https://www.amazon.com/dp/B08XYZ4001",
            "upc": "070501075124",
            "mpn": "6811011",
            "model": "6811011",
            "dimensions": "2.8 x 2.8 x 2.5 in",
            "weight_lbs": 0.35,
            "color": "Translucent",
            "package_quantity": 1,
            "matched": True,
            "profitable": False,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "Walmart",
                    "supplier_title": "Neutrogena Hydro Boost Water Gel Moisturizer, 1.7 oz",
                    "supplier_price": 14.50,
                    "supplier_url": "https://www.walmart.com/ip/Neutrogena-Hydro-Boost/4001",
                    "upc": "070501075124",
                    "mpn": "6811011",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
    ],
    "Pet Supplies": [
        {
            "asin": "B09XYZ5001",
            "title": "KONG Classic Dog Toy, Durable Natural Rubber, Large",
            "brand": "KONG",
            "price": 13.99,
            "url": "https://www.amazon.com/dp/B09XYZ5001",
            "upc": "035585113069",
            "mpn": "CL3",
            "model": "CL3",
            "dimensions": "4.0 x 2.8 x 2.8 in",
            "weight_lbs": 0.5,
            "color": "Red",
            "package_quantity": 1,
            "matched": True,
            "profitable": True,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "Walmart",
                    "supplier_title": "KONG Classic Dog Toy Large Red Natural Rubber",
                    "supplier_price": 6.80,
                    "supplier_url": "https://www.walmart.com/ip/KONG-Classic-Large/5001",
                    "upc": "035585113069",
                    "mpn": "CL3",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
    ],
    "Electronics": [
        {
            "asin": "B08XYZ6001",
            "title": "Anker 10000mAh Portable Charger PowerCore Slim, High-Speed Charging",
            "brand": "Anker",
            "price": 25.99,
            "url": "https://www.amazon.com/dp/B08XYZ6001",
            "upc": "848061073139",
            "mpn": "A1263011",
            "model": "A1263011",
            "dimensions": "5.9 x 2.7 x 0.6 in",
            "weight_lbs": 0.47,
            "color": "Black",
            "package_quantity": 1,
            "matched": True,
            "profitable": True,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "AliExpress",
                    "supplier_title": "Anker PowerCore Slim 10000mAh External Battery Bank",
                    "supplier_price": 12.00,
                    "supplier_url": "https://www.aliexpress.com/item/10000Anker/6001.html",
                    "upc": "848061073139",
                    "mpn": "A1263011",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
        {
            "asin": "B07XYZ6002",
            "title": "TP-Link AC1750 Smart WiFi Router, Dual Band Gigabit",
            "brand": "TP-Link",
            "price": 59.99,
            "url": "https://www.amazon.com/dp/B07XYZ6002",
            "upc": "845973071219",
            "mpn": "Archer A7",
            "model": "Archer A7",
            "dimensions": "9.6 x 6.4 x 1.3 in",
            "weight_lbs": 1.15,
            "color": "Black",
            "package_quantity": 1,
            "matched": False,
            "profitable": False,
            "simulated": True,
            "mismatch_reason": "Model/MPN conflict: Amazon 'archer a7' vs Supplier 'archer c6'",
            "supplier_candidates": [
                {
                    "supplier_name": "Walmart",
                    "supplier_title": "TP-Link AC1200 Smart Wireless Router Archer C6",
                    "supplier_price": 39.99,
                    "supplier_url": "https://www.walmart.com/ip/TP-Link-Router/6002",
                    "upc": "845973071888",
                    "mpn": "Archer C6",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        },
    ],
}

# Fall-back default for unspecified categories
_DEFAULT_DEMO = [
    {
        "asin": "B00DEMO0001",
        "title": "Demo Product Alpha (Simulated Opportunity)",
        "brand": "Demo Brand",
        "price": 29.99,
        "url": "https://www.amazon.com/dp/B00DEMO0001",
        "upc": "123456789012",
        "mpn": "ALPHA-01",
        "matched": True,
        "profitable": True,
        "simulated": True,
        "supplier_candidates": [
            {
                "supplier_name": "Walmart",
                "supplier_title": "Demo Product Alpha Brand Equivalent",
                "supplier_price": 14.99,
                "supplier_url": "https://www.walmart.com/ip/Demo-Alpha/9001",
                "upc": "123456789012",
                "mpn": "ALPHA-01",
                "package_quantity": 1,
                "in_stock": True,
            }
        ],
    }
]


def demo_category_products(category: str, max_products: int = 100) -> List[Dict[str, Any]]:
    """Return stub Amazon products for a demo category scan."""
    products = _DEMO_PRODUCTS.get(category, _DEFAULT_DEMO)
    return [dict(p, simulated=True) for p in products[:max_products]]


def demo_seller_products(seller_id_or_url: str) -> List[Dict[str, Any]]:
    """Return stub products for a demo seller scan."""
    return [
        {
            "asin": "B00DEMO0010",
            "title": f"Demo Seller Product (Simulated) — seller: {seller_id_or_url}",
            "brand": "Demo Seller Brand",
            "price": 34.99,
            "url": "https://www.amazon.com/dp/B00DEMO0010",
            "upc": "987654321098",
            "mpn": "SELLER-10",
            "matched": True,
            "profitable": True,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "Home Depot",
                    "supplier_title": f"Demo Seller Product Store Equivalent — {seller_id_or_url}",
                    "supplier_price": 16.50,
                    "supplier_url": "https://www.homedepot.com/p/Demo-Seller-Product/9010",
                    "upc": "987654321098",
                    "mpn": "SELLER-10",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        }
    ]


def demo_product_by_asin(asin: str) -> List[Dict[str, Any]]:
    """Return a single stub product for a demo ASIN scan."""
    # Look up in demo products first if available
    for cat, prods in _DEMO_PRODUCTS.items():
        for p in prods:
            if p.get("asin") == asin:
                return [dict(p, simulated=True)]

    clean_asin = asin or "B00DEMO9999"
    return [
        {
            "asin": clean_asin,
            "title": f"Demo Product for ASIN {clean_asin} (Simulated)",
            "brand": "Demo Brand",
            "price": 24.99,
            "url": f"https://www.amazon.com/dp/{clean_asin}",
            "upc": "555666777888",
            "mpn": f"MPN-{clean_asin}",
            "matched": True,
            "profitable": True,
            "simulated": True,
            "supplier_candidates": [
                {
                    "supplier_name": "Walmart",
                    "supplier_title": f"Demo Product for ASIN {clean_asin} Wholesale Equivalent",
                    "supplier_price": 11.20,
                    "supplier_url": f"https://www.walmart.com/ip/Demo-{clean_asin}/9999",
                    "upc": "555666777888",
                    "mpn": f"MPN-{clean_asin}",
                    "package_quantity": 1,
                    "in_stock": True,
                }
            ],
        }
    ]


def demo_find_supplier_candidates(
    amazon_product: Dict[str, Any],
    selected_suppliers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Find candidate supplier products for an Amazon listing.
    Filters by selected suppliers if specified (e.g. ['walmart', 'home_depot']).
    """
    candidates = amazon_product.get("supplier_candidates", [])
    if not candidates:
        # Generate default candidate derived from product
        sp_name = "Walmart"
        if selected_suppliers and len(selected_suppliers) > 0:
            sp_name = selected_suppliers[0].replace("_", " ").title()
        candidates = [
            {
                "supplier_name": sp_name,
                "supplier_title": amazon_product.get("title", ""),
                "supplier_price": round(float(amazon_product.get("price", 30)) * 0.60, 2),
                "supplier_url": f"https://www.supplier-demo.com/item/{amazon_product.get('asin', 'demo')}",
                "upc": amazon_product.get("upc", ""),
                "mpn": amazon_product.get("mpn", ""),
                "package_quantity": amazon_product.get("package_quantity", 1),
                "in_stock": True,
            }
        ]

    if selected_suppliers:
        # Normalize comparison (e.g. 'home_depot' -> 'homedepot')
        allowed = {s.replace("_", "").lower() for s in selected_suppliers}
        filtered = [
            c for c in candidates
            if c.get("supplier_name", "").replace(" ", "").replace("'", "").lower() in allowed
        ]
        return filtered if filtered else candidates

    return candidates
