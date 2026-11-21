"""
Phase 5 — Multi-Stage Product Matching Engine.

Implements the 4-stage pipeline specified in fullplan.md:
  Stage 1: Exact identifier verification (UPC, EAN, GTIN, MPN, Model number, Brand)
  Stage 2: Deterministic specification and text comparison (Titles, brands, pack counts, models, condition)
  Stage 3: Candidate ranking across multiple supplier listings
  Stage 4: Confidence banding and final decision routing (Accepted, Review, Rejected)
"""
from typing import Dict, Any, List, Optional, Tuple
import re

ENGINE_VERSION = "v5.0-deterministic"

# ─── Confidence Bands (Section 5.2) ───────────────────────────────────────────
BAND_STRONG = "strong_match"      # 95–100: automatic acceptance eligible
BAND_LIKELY = "likely_match"      # 80–94: likely match
BAND_REVIEW = "manual_review"     # 60–79: requires manual review
BAND_REJECT = "rejected"          # Below 60: reject

# Backwards compatibility constants
MATCH_EXACT = "exact"
MATCH_HIGH = "high"
MATCH_MEDIUM = "medium"
MATCH_LOW = "low"
MATCH_NONE = "none"


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation and extra whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _token_jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity."""
    if not a or not b:
        return 0.0
    set_a = set(_normalise(a).split())
    set_b = set(_normalise(b).split())
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def extract_pack_count(text: str) -> Optional[int]:
    """Extract package quantity from title or spec."""
    if not text:
        return None
    patterns = [
        r"\bpack\s+of\s+(\d+)\b",
        r"\b(\d+)\s*[- ]?(?:pack|pk|count|ct)\b",
        r"\b(?:set|lot)\s+of\s+(\d+)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            try:
                val = int(m.group(1))
                if 1 <= val <= 200:
                    return val
            except (ValueError, TypeError):
                pass
    return None


class MatchingEngine:
    """Multi-stage deterministic matching engine."""

    @classmethod
    def evaluate_pair(
        cls,
        amazon_product: Dict[str, Any],
        supplier_product: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute Stages 1, 2, and 4 on a single candidate pair.
        Returns a complete match record with score, confidence band, differences, and decision.
        """
        differences: List[str] = []
        score = 0.0
        match_type = "none"
        match_method = "none"

        az_title = amazon_product.get("title") or ""
        sp_title = supplier_product.get("title") or ""

        az_brand = _normalise(amazon_product.get("brand") or "")
        sp_brand = _normalise(supplier_product.get("brand") or "")

        az_upc = str(amazon_product.get("upc") or "").strip()
        sp_upc = str(supplier_product.get("upc") or "").strip()

        az_mpn = str(amazon_product.get("mpn") or amazon_product.get("model") or "").strip().lower()
        sp_mpn = str(supplier_product.get("mpn") or supplier_product.get("model") or "").strip().lower()

        # ── Critical Mismatch 1: Brand Conflict ──────────────────────────────
        if az_brand and sp_brand and az_brand != sp_brand:
            # Check if one is a substring of the other (e.g. "Cuisinart" vs "Cuisinart Kitchen")
            if az_brand not in sp_brand and sp_brand not in az_brand:
                differences.append(f"Brand conflict: Amazon '{amazon_product.get('brand')}' vs Supplier '{supplier_product.get('brand')}'")

        # ── Critical Mismatch 2: Model / MPN Conflict ─────────────────────────
        if az_mpn and sp_mpn and az_mpn != sp_mpn:
            differences.append(f"Model number conflict (Model/MPN conflict): Amazon '{az_mpn}' vs Supplier '{sp_mpn}'")

        # ── Critical Mismatch 3: Pack Count / Quantity Conflict ──────────────
        az_pack = extract_pack_count(az_title) or amazon_product.get("package_quantity")
        sp_pack = extract_pack_count(sp_title) or supplier_product.get("package_quantity")
        if az_pack and sp_pack and int(az_pack) != int(sp_pack):
            differences.append(f"Pack count discrepancy (Package quantity discrepancy): Amazon={az_pack} vs Supplier={sp_pack}")

        # ── Critical Mismatch 4: Condition Conflict ──────────────────────────
        az_cond = (amazon_product.get("condition") or "new").lower()
        sp_cond = (supplier_product.get("condition") or "new").lower()
        if az_cond == "new" and ("refurbished" in sp_cond or "used" in sp_cond or "open box" in sp_title.lower()):
            differences.append(f"Condition discrepancy: Amazon is new vs Supplier is {sp_cond}")

        # ── STAGE 1: Exact Identifiers ────────────────────────────────────────
        has_critical_error = any("conflict" in d or "discrepancy" in d for d in differences)

        if not has_critical_error and az_upc and sp_upc and az_upc == sp_upc:
            score = 100.0
            match_type = "exact"
            match_method = "upc"
        elif not has_critical_error and az_mpn and sp_mpn and az_mpn == sp_mpn:
            score = 98.0
            match_type = "exact"
            match_method = "mpn"

        # ── STAGE 2: Deterministic Specification & Text Comparison ────────────
        if score == 0.0:
            if any("Brand conflict" in d for d in differences):
                score = 0.0
                match_type = "brand_mismatch"
                match_method = "none"
            elif any("Model" in d and "conflict" in d for d in differences):
                score = 0.0
                match_type = "mismatch"
                match_method = "none"
            elif any("discrepancy" in d for d in differences):
                score = 35.0  # MATCH_LOW, routes to BAND_REJECT
                match_type = "pack_mismatch"
                match_method = "pack_mismatch"
            else:
                title_sim = _token_jaccard(az_title, sp_title)
                base_score = title_sim * 100.0

                if az_brand and sp_brand and (az_brand == sp_brand or az_brand in sp_brand):
                    base_score = min(100.0, base_score + 5.0)

                penalty = len(differences) * 35.0
                score = max(0.0, min(100.0, base_score - penalty))

                if score >= 80.0:
                    match_type = "spec_match"
                    match_method = "title"
                elif score >= 50.0:
                    match_type = "partial_match"
                    match_method = "title"
                else:
                    match_type = "mismatch" if differences else "low_similarity"
                    match_method = "title"

        # ── STAGE 4: Final Decision & Confidence Bands ────────────────────────
        if score >= 95.0:
            band = BAND_STRONG
            decision = "accepted"
            manual_review = False
            confidence = MATCH_EXACT if match_type == "exact" else MATCH_HIGH
        elif score >= 80.0:
            band = BAND_LIKELY
            decision = "accepted"
            manual_review = False
            confidence = MATCH_HIGH
        elif score >= 50.0:
            band = BAND_REVIEW
            decision = "review"
            manual_review = True
            confidence = MATCH_MEDIUM
        elif score >= 25.0:
            band = BAND_REJECT
            decision = "rejected"
            manual_review = False
            confidence = MATCH_LOW
        else:
            band = BAND_REJECT
            decision = "rejected"
            manual_review = False
            confidence = MATCH_NONE

        mismatch_reason = "; ".join(differences) if differences else None

        # Explanation summary
        if match_type == "exact":
            explanation = f"Exact match verified by {match_method.upper()}."
        elif decision == "accepted":
            explanation = f"Strong specification match ({score:.0f}% confidence)."
        elif manual_review:
            diff_text = "; ".join(differences) if differences else "Moderate similarity requires verification"
            explanation = f"Uncertain candidate flagged for manual review: {diff_text}."
        else:
            diff_text = "; ".join(differences) if differences else "Insufficient similarity"
            explanation = f"Rejected: {diff_text}."

        return {
            "matched": decision in ("accepted", "review"),
            "confidence": confidence,
            "confidence_band": band,
            "score": round(score / 100.0, 4),
            "deterministic_score": round(score, 1),
            "match_type": match_type,
            "match_method": match_method,
            "mismatch_reason": mismatch_reason,
            "explanation": explanation,
            "differences": differences,
            "manual_review": manual_review,
            "final_decision": decision,
            "engine_version": ENGINE_VERSION,
        }

    @classmethod
    def rank_candidates(
        cls,
        amazon_product: Dict[str, Any],
        supplier_candidates: List[Dict[str, Any]],
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Stage 3: Rank multiple supplier candidate listings for an Amazon product.
        Returns sorted list of (candidate, match_record) tuples by deterministic score descending.
        """
        ranked = []
        for candidate in supplier_candidates:
            match_record = cls.evaluate_pair(amazon_product, candidate)
            ranked.append((candidate, match_record))

        # Sort by deterministic score descending
        ranked.sort(key=lambda item: item[1]["deterministic_score"], reverse=True)
        return ranked


# ─── Public Compatibility Wrappers ────────────────────────────────────────────

def match_product(
    amazon_product: Dict[str, Any],
    supplier_product: Dict[str, Any],
) -> Dict[str, Any]:
    """Phase 5 entry point for comparing a product pair."""
    return MatchingEngine.evaluate_pair(amazon_product, supplier_product)


def match_product_demo(amazon_product: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 5 demo stub matcher respecting embedded demo flags and differences."""
    already_matched = bool(amazon_product.get("matched", False))
    mismatch_reason = amazon_product.get("mismatch_reason")
    differences = [mismatch_reason] if mismatch_reason else []

    if already_matched:
        return {
            "matched": True,
            "confidence": MATCH_EXACT,
            "confidence_band": BAND_STRONG,
            "score": 1.0,
            "deterministic_score": 100.0,
            "match_type": "exact",
            "match_method": amazon_product.get("match_method", "demo_stub"),
            "explanation": "Verified demo match.",
            "differences": [],
            "manual_review": False,
            "final_decision": "accepted",
            "engine_version": ENGINE_VERSION,
        }
    else:
        score = 65.0 if "discrepancy" in str(mismatch_reason) else 0.0
        manual_review = bool(score >= 60.0)
        band = BAND_REVIEW if manual_review else BAND_REJECT
        return {
            "matched": manual_review,
            "confidence": MATCH_LOW if score > 0 else MATCH_NONE,
            "confidence_band": band,
            "score": round(score / 100.0, 2),
            "deterministic_score": score,
            "match_type": "mismatch" if differences else "none",
            "match_method": "demo_stub",
            "explanation": mismatch_reason or "No match found.",
            "differences": differences,
            "manual_review": manual_review,
            "final_decision": "review" if manual_review else "rejected",
            "engine_version": ENGINE_VERSION,
        }
