"""
Profitability Calculation Engine (Phase 7).

Calculates potential net profit, gross margin, and ROI independently across all 4 fulfillment methods:
  1. Amazon FBA
  2. Amazon FBM
  3. Walmart WFS
  4. Walmart Seller-Fulfilled

Supports custom Fee Profiles, expense itemization, calculation certainty status,
and division-by-zero guards.
"""
from typing import Dict, Any, Optional, List
import math

# ─── Default Fee Assumptions ──────────────────────────────────────────────────

DEFAULT_REFERRAL_RATE = 0.15  # 15 %
FBA_BASE_FEE = 3.22           # USD small standard
WFS_BASE_FEE = 3.45           # USD base WFS fulfillment
CARRIER_FBM_BASE = 4.50       # Outbound shipping base for seller-fulfilled


def _estimate_fba_fee(weight_lbs: Optional[float] = None) -> float:
    """Tiered FBA fee estimation based on package weight."""
    if not weight_lbs or weight_lbs <= 0.5:
        return 3.22
    if weight_lbs <= 1.0:
        return 3.75
    if weight_lbs <= 2.0:
        return 4.75
    if weight_lbs <= 3.0:
        return 5.40
    # Over 3 lbs: $5.40 + $0.38 per extra lb
    return round(5.40 + (weight_lbs - 3.0) * 0.38, 2)


def _estimate_cubic_feet(dimensions_str: Optional[str] = None) -> float:
    """Parse dimensions string e.g. '9.0 x 7.7 x 14.0 in' into cubic feet."""
    if not dimensions_str:
        return 0.15  # Default ~0.15 cu ft for standard small product
    import re
    numbers = [float(n) for n in re.findall(r"\d+\.?\d*", dimensions_str)]
    if len(numbers) >= 3:
        cubic_inches = numbers[0] * numbers[1] * numbers[2]
        return round(cubic_inches / 1728.0, 3)
    return 0.15


def calculate_method_pnl(
    method: str,
    selling_price: float,
    product_cost: float,
    weight_lbs: Optional[float] = None,
    dimensions_str: Optional[str] = None,
    profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate full P&L for a specific fulfillment method.
    Guards against division-by-zero, handles missing cost, and tracks calculation status.
    """
    selling_price = max(0.0, float(selling_price or 0.0))
    product_cost = max(0.0, float(product_cost or 0.0))
    prof = profile or {}

    # Determine calculation status (verified, estimated, incomplete)
    if product_cost <= 0.0:
        status = "incomplete"
    elif weight_lbs is None or weight_lbs <= 0:
        status = "estimated"
    else:
        status = "verified"

    # 1. Referral Fee
    referral_rate = float(prof.get("referral_fee_pct", DEFAULT_REFERRAL_RATE * 100)) / 100.0
    referral_fee = round(selling_price * referral_rate, 2)

    # 2. Fulfillment Fee & Shipping
    cu_ft = _estimate_cubic_feet(dimensions_str)
    weight = weight_lbs if weight_lbs and weight_lbs > 0 else 1.0

    if method == "amazon_fba":
        fulfillment_fee = float(prof.get("fulfillment_fee_flat") or _estimate_fba_fee(weight_lbs))
        inbound_rate = float(prof.get("inbound_shipping_per_lb", 0.45))
        inbound_shipping = round(weight * inbound_rate, 2)
        outbound_shipping = 0.0
        prep_cost = float(prof.get("prep_cost_per_unit", 1.00))
        packaging_cost = float(prof.get("packaging_cost_per_unit", 0.50))
        storage_rate = float(prof.get("storage_fee_monthly_per_cuft", 0.87))
        storage_fee = round(cu_ft * storage_rate, 2)
        labor_handling = 0.0
    elif method == "amazon_fbm":
        fulfillment_fee = 0.0
        inbound_shipping = 0.0
        outbound_shipping = round(CARRIER_FBM_BASE + (weight * 0.60), 2)
        prep_cost = float(prof.get("prep_cost_per_unit", 0.50))
        packaging_cost = float(prof.get("packaging_cost_per_unit", 0.85))
        storage_fee = 0.0
        labor_handling = float(prof.get("handling_per_order", 1.50))
    elif method == "walmart_wfs":
        fulfillment_fee = float(prof.get("fulfillment_fee_flat", WFS_BASE_FEE))
        inbound_rate = float(prof.get("inbound_shipping_per_lb", 0.40))
        inbound_shipping = round(weight * inbound_rate, 2)
        outbound_shipping = 0.0
        prep_cost = float(prof.get("prep_cost_per_unit", 0.90))
        packaging_cost = float(prof.get("packaging_cost_per_unit", 0.40))
        storage_rate = float(prof.get("storage_fee_monthly_per_cuft", 0.75))
        storage_fee = round(cu_ft * storage_rate, 2)
        labor_handling = 0.0
    else:  # walmart_sf
        fulfillment_fee = 0.0
        inbound_shipping = 0.0
        outbound_shipping = round(CARRIER_FBM_BASE + (weight * 0.60), 2)
        prep_cost = float(prof.get("prep_cost_per_unit", 0.50))
        packaging_cost = float(prof.get("packaging_cost_per_unit", 0.85))
        storage_fee = 0.0
        labor_handling = float(prof.get("handling_per_order", 1.50))

    overhead = float(prof.get("misc_overhead_flat", 0.25))

    itemized_fees = {
        "referral_fee": referral_fee,
        "fulfillment_fee": fulfillment_fee,
        "inbound_shipping": inbound_shipping,
        "outbound_shipping": outbound_shipping,
        "prep_cost": prep_cost,
        "packaging_cost": packaging_cost,
        "storage_fee": storage_fee,
        "labor_handling": labor_handling,
        "overhead": overhead,
    }

    total_fees = round(sum(itemized_fees.values()), 2)
    total_cost = round(product_cost + total_fees, 2)
    net_profit = round(selling_price - total_cost, 2)

    # Margin & ROI (division by zero guarded)
    margin_pct = round((net_profit / selling_price * 100), 2) if selling_price > 0 else 0.0
    roi_pct = round((net_profit / product_cost * 100), 2) if product_cost > 0 else 0.0

    # Break even price
    non_ref_costs = total_cost - referral_fee
    break_even = round(non_ref_costs / (1.0 - referral_rate), 2) if (1.0 - referral_rate) > 0 else total_cost

    return {
        "method": method,
        "profitable": net_profit > 0 and product_cost > 0,
        "net_profit": net_profit,
        "roi_pct": roi_pct,
        "margin_pct": margin_pct,
        "break_even_price": break_even,
        "total_fees": total_fees,
        "total_cost": total_cost,
        "itemized_fees": itemized_fees,
        "calculation_status": status,
    }


def calculate_all_fulfillment_methods(
    amazon_price: float,
    cost_price: float,
    weight_lbs: Optional[float] = None,
    dimensions_str: Optional[str] = None,
    profiles_by_method: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Calculate P&L across all four methods, pick best method, and return unified summary.
    """
    methods = ["amazon_fba", "amazon_fbm", "walmart_wfs", "walmart_sf"]
    breakdown: Dict[str, Any] = {}
    profiles = profiles_by_method or {}

    for m in methods:
        prof = profiles.get(m)
        breakdown[m] = calculate_method_pnl(
            method=m,
            selling_price=amazon_price,
            product_cost=cost_price,
            weight_lbs=weight_lbs,
            dimensions_str=dimensions_str,
            profile=prof,
        )

    # Pick best fulfillment method by net profit
    best_method = max(methods, key=lambda m: breakdown[m]["net_profit"])
    best_pnl = breakdown[best_method]

    return {
        "profitable": best_pnl["profitable"],
        "net_profit": best_pnl["net_profit"],
        "roi_pct": best_pnl["roi_pct"],
        "margin_pct": best_pnl["margin_pct"],
        "break_even_price": best_pnl["break_even_price"],
        "total_fees": best_pnl["total_fees"],
        "total_cost": best_pnl["total_cost"],
        "referral_fee": best_pnl["itemized_fees"]["referral_fee"],
        "fba_fee": best_pnl["itemized_fees"]["fulfillment_fee"],
        "total_profit": best_pnl["net_profit"],
        "supplier_cost": cost_price,
        "best_fulfillment_method": best_method,
        "calculation_status": best_pnl["calculation_status"],
        "fulfillment_breakdown": breakdown,
        "itemized_expenses": best_pnl["itemized_fees"],
    }


# ─── Backward Compatibility Wrappers ──────────────────────────────────────────

def calculate_profitability(
    amazon_price: float,
    cost_price: float,
    fulfillment_method: str = "amazon_fba",
    units: int = 1,
) -> Dict[str, Any]:
    """Backward-compatible single-method wrapper."""
    pnl = calculate_method_pnl(
        method=fulfillment_method,
        selling_price=amazon_price,
        product_cost=cost_price,
    )
    # In Phase 4, total_cost represented the baseline direct cost prior to marketplace referral fee
    direct_cost = round(cost_price + pnl["itemized_fees"]["fulfillment_fee"], 2)
    return {
        "profitable": pnl["profitable"],
        "net_profit": pnl["net_profit"],
        "roi_pct": pnl["roi_pct"],
        "margin_pct": pnl["margin_pct"],
        "referral_fee": pnl["itemized_fees"]["referral_fee"],
        "fba_fee": pnl["itemized_fees"]["fulfillment_fee"],
        "total_fees": pnl["total_fees"],
        "total_cost": direct_cost,
        "break_even_price": pnl["break_even_price"],
        "total_profit": round(pnl["net_profit"] * units, 2),
        "supplier_cost": cost_price,
        "calculation_status": pnl["calculation_status"],
    }


def calculate_profitability_demo(amazon_product: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible demo profitability calculator evaluating all 4 methods."""
    amazon_price = float(amazon_product.get("price") or 29.99)
    simulated_cost = round(amazon_price * 0.60, 2)
    weight_lbs = amazon_product.get("weight_lbs")
    dimensions_str = amazon_product.get("dimensions")

    res = calculate_all_fulfillment_methods(
        amazon_price=amazon_price,
        cost_price=simulated_cost,
        weight_lbs=weight_lbs,
        dimensions_str=dimensions_str,
    )

    if "profitable" in amazon_product:
        res["profitable"] = bool(amazon_product["profitable"])
    res["simulated"] = True
    return res
