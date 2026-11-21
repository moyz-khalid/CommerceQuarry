"""
Realistic Simulated Walmart Seller Catalog Provider (Phase 12).
Provides comprehensive, multi-seller, multi-category catalogs with realistic
exact matches, likely matches, bundle count discrepancies, and non-matches.
All records are explicitly marked as DEMO DATA.
"""
from typing import List, Dict, Any, Optional, Tuple
from app.services.walmart.base import WalmartProviderBase, WalmartProduct, WalmartSellerInfo
from app.services.walmart.normalizer import normalize_walmart_product
from app.services.walmart.seller_service import parse_walmart_seller_url


DEMO_SELLERS: Dict[str, Dict[str, Any]] = {
    "101001": {
        "seller_id": "101001",
        "seller_name": "ProTools & Hardware Depot",
        "storefront_url": "https://www.walmart.com/seller/101001",
        "product_count": 8,
        "rating": 4.8,
        "is_verified": True,
        "is_demo": True,
        "products": [
            {
                "walmart_product_id": "WM-70101",
                "product_title": "DEWALT 20V MAX Cordless Compact Drill/Impact Driver Combo Kit (2-Tool)",
                "current_price": 139.00,
                "original_price": 169.00,
                "brand": "DEWALT",
                "upc": "028877514573",
                "mpn": "DCK240C2",
                "model_number": "DCK240C2",
                "category": "Tools & Hardware",
                "weight_lbs": 9.2,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1504148455328-c376907d081c?w=400",
                "product_url": "https://www.walmart.com/ip/DEWALT-DCK240C2/70101",
                # Sourcing match hint: Home Depot sells at $99.00 -> $40 gross margin!
            },
            {
                "walmart_product_id": "WM-70102",
                "product_title": "Milwaukee M18 18V Lithium-Ion Brushless Cordless 1/2 in. Compact Drill/Driver",
                "current_price": 129.00,
                "original_price": 149.00,
                "brand": "Milwaukee",
                "upc": "045242512393",
                "mpn": "2801-20",
                "model_number": "2801-20",
                "category": "Tools & Hardware",
                "weight_lbs": 3.8,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=400",
                "product_url": "https://www.walmart.com/ip/Milwaukee-2801-20/70102",
                # Sourcing match hint: Home Depot sells at $89.00
            },
            {
                "walmart_product_id": "WM-70103",
                "product_title": "Stanley FatMax 25-ft Tape Measure Extra Wide Blade",
                "current_price": 28.95,
                "original_price": 32.99,
                "brand": "Stanley",
                "upc": "076174330591",
                "mpn": "FMHT33865S",
                "model_number": "FMHT33865S",
                "category": "Tools & Hardware",
                "weight_lbs": 1.1,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1572981779307-38b8cabb2407?w=400",
                "product_url": "https://www.walmart.com/ip/Stanley-FatMax-25ft/70103",
                # Sourcing match hint: Lowe's sells at $14.98
            },
            {
                "walmart_product_id": "WM-70104",
                "product_title": "Klein Tools 11-in-1 Screwdriver / Nut Driver Multi-Tool with Cushion Grip",
                "current_price": 24.97,
                "original_price": 27.99,
                "brand": "Klein Tools",
                "upc": "092644325000",
                "mpn": "32500",
                "model_number": "32500",
                "category": "Tools & Hardware",
                "weight_lbs": 0.5,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=400",
                "product_url": "https://www.walmart.com/ip/Klein-Tools-32500/70104",
                # Sourcing match hint: Home Depot sells at $14.97
            },
            {
                "walmart_product_id": "WM-70105",
                "product_title": "3M Scotch 2090 Blue Original Multi-Surface Painter's Tape (Pack of 3)",
                "current_price": 29.98,
                "original_price": 34.50,
                "brand": "3M",
                "upc": "051115036814",
                "mpn": "2090-3PK",
                "model_number": "2090",
                "category": "Paint & Supplies",
                "weight_lbs": 1.2,
                "package_quantity": 3,
                "image_url": "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=400",
                "product_url": "https://www.walmart.com/ip/3M-Scotch-2090-3PK/70105",
                # Tests package quantity check: supplier single roll vs pack of 3!
            },
            {
                "walmart_product_id": "WM-70106",
                "product_title": "Husky 100-Piece Mechanics Tool Set with Tough Plastic Storage Case",
                "current_price": 89.97,
                "original_price": 109.00,
                "brand": "Husky",
                "upc": "820909567890",
                "mpn": "H100MTS",
                "model_number": "H100MTS",
                "category": "Tools & Hardware",
                "weight_lbs": 12.5,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1581092162384-8987c1d64718?w=400",
                "product_url": "https://www.walmart.com/ip/Husky-H100MTS/70106",
                # Sourcing match hint: Home Depot exclusive brand
            },
            {
                "walmart_product_id": "WM-70107",
                "product_title": "Gorilla Heavy Duty Double-Sided Mounting Tape XL 1 in. x 120 in. Black",
                "current_price": 17.88,
                "original_price": 19.99,
                "brand": "Gorilla",
                "upc": "052427606505",
                "mpn": "6065001",
                "model_number": "6065001",
                "category": "Hardware",
                "weight_lbs": 0.4,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=400",
                "product_url": "https://www.walmart.com/ip/Gorilla-Mounting-Tape/70107",
            },
            {
                "walmart_product_id": "WM-70108",
                "product_title": "Commercial Electric 7-in-1 Wire Stripper and Wire Cutter Hand Tool",
                "current_price": 18.50,
                "original_price": 21.00,
                "brand": "Commercial Electric",
                "upc": "744500112233",
                "mpn": "CE-WS71",
                "model_number": "CE-WS71",
                "category": "Electrical",
                "weight_lbs": 0.6,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1581092335397-9583fe92d232?w=400",
                "product_url": "https://www.walmart.com/ip/Commercial-Electric-CE-WS71/70108",
            },
        ],
    },
    "101002": {
        "seller_id": "101002",
        "seller_name": "PrimeHome & Kitchen Essentials",
        "storefront_url": "https://www.walmart.com/seller/101002",
        "product_count": 6,
        "rating": 4.7,
        "is_verified": True,
        "is_demo": True,
        "products": [
            {
                "walmart_product_id": "WM-80201",
                "product_title": "Rubbermaid Brilliance Leak-Proof Food Storage Containers 10-Piece Set",
                "current_price": 34.99,
                "original_price": 39.99,
                "brand": "Rubbermaid",
                "upc": "071691508906",
                "mpn": "2108369",
                "model_number": "2108369",
                "category": "Home & Kitchen",
                "weight_lbs": 2.8,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=400",
                "product_url": "https://www.walmart.com/ip/Rubbermaid-Brilliance/80201",
            },
            {
                "walmart_product_id": "WM-80202",
                "product_title": "Brita Standard Water Filter Replacement Cartridges for Pitchers (6-Pack)",
                "current_price": 39.98,
                "original_price": 44.99,
                "brand": "Brita",
                "upc": "060258355030",
                "mpn": "35503",
                "model_number": "35503",
                "category": "Home & Kitchen",
                "weight_lbs": 1.5,
                "package_quantity": 6,
                "image_url": "https://images.unsplash.com/photo-1548839140-29a749e1bc4e?w=400",
                "product_url": "https://www.walmart.com/ip/Brita-Filters-6PK/80202",
            },
            {
                "walmart_product_id": "WM-80203",
                "product_title": "Lodge 10.25 Inch Pre-Seasoned Cast Iron Skillet with Silicone Hot Handle Holder",
                "current_price": 29.90,
                "original_price": 34.90,
                "brand": "Lodge",
                "upc": "075536301037",
                "mpn": "L8SK3",
                "model_number": "L8SK3",
                "category": "Cookware",
                "weight_lbs": 5.4,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1584990347449-39b566580e0c?w=400",
                "product_url": "https://www.walmart.com/ip/Lodge-Cast-Iron-Skillet/80203",
            },
            {
                "walmart_product_id": "WM-80204",
                "product_title": "OXO Good Grips 3-Piece Angled Measuring Cup Set Clear Plastic",
                "current_price": 27.95,
                "original_price": 31.95,
                "brand": "OXO",
                "upc": "719812015897",
                "mpn": "11158900",
                "model_number": "11158900",
                "category": "Kitchen Utensils",
                "weight_lbs": 1.2,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=400",
                "product_url": "https://www.walmart.com/ip/OXO-Measuring-Cup-Set/80204",
            },
            {
                "walmart_product_id": "WM-80205",
                "product_title": "Simplehuman 45 Liter / 12 Gallon Custom Fit Trash Can Liners Code M (60 Count)",
                "current_price": 32.50,
                "original_price": 36.00,
                "brand": "Simplehuman",
                "upc": "838810008592",
                "mpn": "CW0173",
                "model_number": "CW0173",
                "category": "Cleaning & Storage",
                "weight_lbs": 2.1,
                "package_quantity": 60,
                "image_url": "https://images.unsplash.com/photo-1584269600464-37b1b58a9fe7?w=400",
                "product_url": "https://www.walmart.com/ip/Simplehuman-Liners-Code-M/80205",
            },
            {
                "walmart_product_id": "WM-80206",
                "product_title": "Shark Navigator Lift-Away Upright Vacuum with Anti-Allergen Seal NV352",
                "current_price": 179.00,
                "original_price": 199.99,
                "brand": "Shark",
                "upc": "622356534567",
                "mpn": "NV352",
                "model_number": "NV352",
                "category": "Vacuums & Floor Care",
                "weight_lbs": 13.7,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1558317374-067fb5f30001?w=400",
                "product_url": "https://www.walmart.com/ip/Shark-Navigator-NV352/80206",
            },
        ],
    },
    "101003": {
        "seller_id": "101003",
        "seller_name": "GlobalTech Direct Electronics",
        "storefront_url": "https://www.walmart.com/seller/101003",
        "product_count": 5,
        "rating": 4.6,
        "is_verified": True,
        "is_demo": True,
        "products": [
            {
                "walmart_product_id": "WM-90301",
                "product_title": "Anker 735 Charger (GaNPrime 65W) 3-Port Fast Compact Wall Adapter",
                "current_price": 49.99,
                "original_price": 59.99,
                "brand": "Anker",
                "upc": "194644098674",
                "mpn": "A2668",
                "model_number": "A2668",
                "category": "Electronics & Accessories",
                "weight_lbs": 0.4,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=400",
                "product_url": "https://www.walmart.com/ip/Anker-735-Charger/90301",
            },
            {
                "walmart_product_id": "WM-90302",
                "product_title": "UGREEN USB C Hub 6-in-1 Dongle with 4K HDMI 100W PD 3 USB 3.0 Ports",
                "current_price": 29.99,
                "original_price": 35.99,
                "brand": "UGREEN",
                "upc": "695730386789",
                "mpn": "CM511",
                "model_number": "CM511",
                "category": "Electronics & Accessories",
                "weight_lbs": 0.3,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=400",
                "product_url": "https://www.walmart.com/ip/UGREEN-USB-C-Hub/90302",
                # Sourcing match hint: AliExpress sells at $12.50
            },
            {
                "walmart_product_id": "WM-90303",
                "product_title": "Baseus 65W Power Bank 20000mAh Laptop Portable Charger Fast Charging",
                "current_price": 54.99,
                "original_price": 64.99,
                "brand": "Baseus",
                "upc": "695315620123",
                "mpn": "PBLG65W",
                "model_number": "PBLG65W",
                "category": "Electronics & Accessories",
                "weight_lbs": 1.1,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1609592424364-c2c54cf94d13?w=400",
                "product_url": "https://www.walmart.com/ip/Baseus-65W-Power-Bank/90303",
                # Sourcing match hint: AliExpress sells at $28.00
            },
            {
                "walmart_product_id": "WM-90304",
                "product_title": "TP-Link Kasa Smart Plug Mini 15A Apple HomeKit Compatible (4-Pack)",
                "current_price": 39.99,
                "original_price": 49.99,
                "brand": "TP-Link",
                "upc": "840030700582",
                "mpn": "EP25P4",
                "model_number": "EP25P4",
                "category": "Smart Home",
                "weight_lbs": 0.8,
                "package_quantity": 4,
                "image_url": "https://images.unsplash.com/photo-1558002038-1055907df827?w=400",
                "product_url": "https://www.walmart.com/ip/TP-Link-Kasa-EP25P4/90304",
            },
            {
                "walmart_product_id": "WM-90305",
                "product_title": "Logitech MK270 Wireless Keyboard and Mouse Combo Long Battery Life",
                "current_price": 27.99,
                "original_price": 32.99,
                "brand": "Logitech",
                "upc": "097855088926",
                "mpn": "920-004536",
                "model_number": "MK270",
                "category": "Computer Accessories",
                "weight_lbs": 1.8,
                "package_quantity": 1,
                "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400",
                "product_url": "https://www.walmart.com/ip/Logitech-MK270/90305",
            },
        ],
    },
}


class DemoWalmartProvider(WalmartProviderBase):
    """
    Simulated Walmart provider providing realistic seller discovery and catalogs
    without requiring third-party credentials. Complies with Phase 12.
    """

    def __init__(self):
        self.provider_name = "walmart_demo"

    def get_provider_name(self) -> str:
        return self.provider_name

    def identify_seller(self, url_or_id: str) -> Optional[WalmartSellerInfo]:
        parsed = parse_walmart_seller_url(url_or_id)
        if not parsed["valid"]:
            return None

        seller_id = parsed["seller_id"]
        # Check if known demo seller, else generate a clean deterministic demo profile
        if seller_id in DEMO_SELLERS:
            s = DEMO_SELLERS[seller_id]
            return WalmartSellerInfo(
                seller_id=s["seller_id"],
                seller_name=s["seller_name"],
                storefront_url=s["storefront_url"],
                product_count=s["product_count"],
                rating=s["rating"],
                is_verified=s["is_verified"],
                provider=self.provider_name,
                is_demo=True,
            )

        # Dynamic demo fallback for any unknown entered seller ID
        return WalmartSellerInfo(
            seller_id=seller_id,
            seller_name=f"Walmart Marketplace Seller {seller_id}",
            storefront_url=f"https://www.walmart.com/seller/{seller_id}",
            product_count=len(DEMO_SELLERS["101001"]["products"]),
            rating=4.7,
            is_verified=True,
            provider=self.provider_name,
            is_demo=True,
        )

    def get_seller_products(
        self,
        seller_id: str,
        limit: int = 50,
        page: int = 1,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
    ) -> Tuple[List[WalmartProduct], Optional[int]]:
        seller_data = DEMO_SELLERS.get(seller_id) or DEMO_SELLERS["101001"]
        seller_name = seller_data["seller_name"]
        raw_items = list(seller_data["products"])

        # Filters
        filtered = []
        for item in raw_items:
            price = float(item.get("current_price", 0))
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            if category and item.get("category", "").lower() != category.lower():
                continue
            filtered.append(item)

        total_count = len(filtered)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paged_items = filtered[start_idx:end_idx]

        products = [
            normalize_walmart_product(
                raw=item,
                provider_name=self.provider_name,
                seller_id=seller_id,
                seller_name=seller_name,
                is_demo=True,
            )
            for item in paged_items
        ]

        return products, total_count

    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "seller_identification": True,
            "seller_products": True,
            "pagination": True,
            "price_filtering": True,
            "category_filtering": True,
            "is_live": False,
            "requires_credentials": False,
            "rate_limit_rps": 50,
            "configured": True,
            "description": "Simulated multi-seller catalog with realistic products across Home & Tools, Kitchen, and Electronics.",
        }
