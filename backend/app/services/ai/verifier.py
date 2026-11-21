"""
DeepSeek AI Verification Service (Phase 6).

Selectively verifies ambiguous candidate matches and enriches the match record
with AI confidence, structured reasoning, differences, and token usage cost tracking.
"""
from typing import Dict, Any, Tuple, Optional
from loguru import logger
from .client import DeepSeekClient, DeepSeekVerificationResult

_client = DeepSeekClient()


def should_verify_with_ai(deterministic_match: Dict[str, Any]) -> bool:
    """
    Section 6.1 Policy:
    Do not send every candidate to AI.
    Skip obvious exact matches (score >= 95).
    Skip obvious mismatches (score < 40 or brand conflicts).
    Send only ambiguous, sufficiently relevant candidates (score 50–85 or manual_review=True).
    """
    score = float(deterministic_match.get("deterministic_score") or (deterministic_match.get("score", 0) * 100))
    differences = deterministic_match.get("differences", [])

    # Exact matches do not require AI
    if score >= 95.0 or deterministic_match.get("match_type") == "exact":
        return False

    # Fatal brand or model conflicts already have definitive rejections
    if any("Brand conflict" in d for d in differences):
        return False

    # Route candidates needing manual review or in ambiguous confidence range
    if deterministic_match.get("manual_review") or deterministic_match.get("confidence_band") == "manual_review":
        return True

    if 50.0 <= score <= 85.0:
        return True

    return False


def build_ai_prompt(
    amazon_product: Dict[str, Any],
    supplier_product: Dict[str, Any],
    deterministic_match: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """
    Section 6.2 AI input:
    Provide available structured fields, explicitly marking missing or unknown fields.
    """
    system_prompt = (
        "You are an expert e-commerce product verification AI for retail arbitrage and wholesale sourcing. "
        "Your task is to analyze an Amazon listing and a candidate supplier listing to verify whether they "
        "represent the EXACT same product opportunity. "
        "Carefully check brand, model number, package quantity (single vs multi-pack), size/dimensions, and condition. "
        "You MUST respond ONLY with a valid JSON object matching the requested schema:\n"
        "{\n"
        '  "is_match": true | false,\n'
        '  "confidence": 0-100,\n'
        '  "match_type": "exact" | "variant" | "different_item" | "uncertain",\n'
        '  "reason": "Detailed explanation of the decision",\n'
        '  "differences": ["list", "of", "differences"],\n'
        '  "manual_review": true | false\n'
        "}"
    )

    def _val(val: Any) -> str:
        if val is None or str(val).strip() == "":
            return "N/A (Not Specified)"
        return str(val).strip()

    diffs_text = "None detected so far"
    if deterministic_match and deterministic_match.get("differences"):
        diffs_text = "; ".join(deterministic_match["differences"])

    user_prompt = f"""Compare the following two product listings:

=== AMAZON LISTING ===
- Title: {_val(amazon_product.get('title'))}
- Brand: {_val(amazon_product.get('brand'))}
- ASIN: {_val(amazon_product.get('asin'))}
- UPC/EAN: {_val(amazon_product.get('upc'))}
- MPN / Model: {_val(amazon_product.get('mpn') or amazon_product.get('model'))}
- Package Quantity: {_val(amazon_product.get('package_quantity'))}
- Dimensions: {_val(amazon_product.get('dimensions'))}
- Weight: {_val(amazon_product.get('weight_lbs'))} lbs
- Color: {_val(amazon_product.get('color'))}
- Condition: {_val(amazon_product.get('condition', 'new'))}
- Price: ${_val(amazon_product.get('price'))}

=== SUPPLIER LISTING ===
- Supplier Marketplace: {_val(supplier_product.get('supplier_name'))}
- Title: {_val(supplier_product.get('supplier_title') or supplier_product.get('title'))}
- Brand: {_val(supplier_product.get('brand'))}
- UPC/EAN: {_val(supplier_product.get('upc'))}
- MPN / Model: {_val(supplier_product.get('mpn') or supplier_product.get('model'))}
- Package Quantity: {_val(supplier_product.get('package_quantity'))}
- Condition: {_val(supplier_product.get('condition', 'new'))}
- Cost: ${_val(supplier_product.get('supplier_price') or supplier_product.get('price'))}

=== DETERMINISTIC SCAN NOTES ===
- Detected Differences: {diffs_text}

Determine whether these two listings refer to the same identical sellable unit. Output strictly valid JSON."""

    return system_prompt, user_prompt


def verify_candidate_match(
    amazon_product: Dict[str, Any],
    supplier_product: Dict[str, Any],
    deterministic_match: Dict[str, Any],
    force: bool = False,
) -> Dict[str, Any]:
    """
    Execute AI verification if eligible or forced, and enrich the match record.
    Returns the updated match record.
    """
    if not force and not should_verify_with_ai(deterministic_match):
        deterministic_match["ai_verified"] = False
        return deterministic_match

    system_prompt, user_prompt = build_ai_prompt(amazon_product, supplier_product, deterministic_match)
    cache_key = _client.get_cache_key(amazon_product, supplier_product)

    ai_result, metadata = _client.verify_product_pair(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        cache_key=cache_key,
    )

    if not ai_result:
        # Fallback to deterministic decision without crashing
        logger.warning(f"AI verification unavailable for ASIN {amazon_product.get('asin')}; retaining deterministic decision.")
        deterministic_match["ai_verified"] = False
        return deterministic_match

    # Merge AI verification into match record
    updated = dict(deterministic_match)
    updated["ai_verified"] = True
    updated["ai_score"] = float(ai_result.confidence)
    updated["ai_decision"] = "accepted" if ai_result.is_match else "rejected"
    updated["ai_reason"] = ai_result.reason
    updated["ai_differences"] = ai_result.differences
    updated["ai_match_type"] = ai_result.match_type
    updated["tokens_used"] = metadata.get("total_tokens", 0)
    updated["ai_cost_usd"] = metadata.get("estimated_cost_usd", 0.0)

    # If AI has high confidence, it can upgrade or adjust the final decision
    if ai_result.confidence >= 90:
        if ai_result.is_match:
            updated["final_decision"] = "accepted"
            updated["matched"] = True
            updated["manual_review"] = False
            updated["confidence_band"] = "strong_match"
        else:
            updated["final_decision"] = "rejected"
            updated["matched"] = False
            updated["manual_review"] = False
            updated["confidence_band"] = "rejected"
    elif ai_result.manual_review:
        updated["final_decision"] = "review"
        updated["manual_review"] = True
        updated["confidence_band"] = "manual_review"

    if ai_result.differences:
        existing_diffs = set(updated.get("differences", []))
        for d in ai_result.differences:
            if d not in existing_diffs:
                updated.setdefault("differences", []).append(d)

    return updated
