"""
Phase 6 Tests — DeepSeek AI Verification Pipeline.

Verifies:
  - Section 6.1: Selective AI policy (only ambiguous candidates sent; exact & obvious mismatches skipped)
  - Section 6.2: Structured prompt formatting with explicitly marked missing fields (N/A)
  - Section 6.3: JSON schema validation with Pydantic model
  - Caching mechanism (prevents repeat API calls for identical product pairs)
  - Token tracking and estimated cost calculation
  - Safe error fallback (AI failure does not crash the scan)
  - On-demand AI verification endpoint (POST /api/scans/{id}/results/{asin}/verify-ai)
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer demo-user"}


# ─── 6.1 Selective AI Policy ─────────────────────────────────────────────────

from app.services.ai.verifier import should_verify_with_ai, build_ai_prompt, verify_candidate_match
from app.services.ai.client import DeepSeekClient, DeepSeekVerificationResult


def test_ai_policy_skips_exact_matches():
    exact_match = {
        "match_type": "exact",
        "deterministic_score": 100.0,
        "score": 1.0,
        "manual_review": False,
        "differences": [],
    }
    assert should_verify_with_ai(exact_match) is False


def test_ai_policy_skips_brand_conflicts():
    brand_conflict = {
        "match_type": "brand_mismatch",
        "deterministic_score": 0.0,
        "score": 0.0,
        "manual_review": False,
        "differences": ["Brand conflict: Amazon 'Cuisinart' vs Supplier 'Hamilton Beach'"],
    }
    assert should_verify_with_ai(brand_conflict) is False


def test_ai_policy_accepts_ambiguous_review_candidates():
    ambiguous = {
        "match_type": "partial_match",
        "deterministic_score": 68.0,
        "score": 0.68,
        "confidence_band": "manual_review",
        "manual_review": True,
        "differences": ["Moderate title similarity"],
    }
    assert should_verify_with_ai(ambiguous) is True


def test_ai_policy_accepts_moderate_score_band():
    moderate = {
        "match_type": "spec_match",
        "deterministic_score": 75.0,
        "score": 0.75,
        "manual_review": False,
        "differences": [],
    }
    assert should_verify_with_ai(moderate) is True


# ─── 6.2 Structured Prompt Formatting ─────────────────────────────────────────

def test_prompt_marks_missing_fields():
    az = {
        "title": "Cuisinart 12-Cup Coffee Maker",
        "brand": "Cuisinart",
        "asin": "B08XYZ1001",
        "upc": "",  # missing
        "mpn": None,  # missing
        "dimensions": "",
        "price": 49.99,
    }
    sp = {
        "supplier_name": "Walmart",
        "title": "Cuisinart 12-Cup Programmable DCC-1200",
        "brand": "Cuisinart",
        "upc": "086279116918",
        "price": 28.50,
    }

    system_prompt, user_prompt = build_ai_prompt(az, sp)

    assert "expert e-commerce product verification AI" in system_prompt
    assert "UPC/EAN: N/A (Not Specified)" in user_prompt
    assert "MPN / Model: N/A (Not Specified)" in user_prompt
    assert "Dimensions: N/A (Not Specified)" in user_prompt
    assert "Cuisinart 12-Cup Coffee Maker" in user_prompt
    assert "Walmart" in user_prompt


# ─── 6.3 Structured Schema Validation ─────────────────────────────────────────

def test_deepseek_result_schema_valid():
    valid_data = {
        "is_match": True,
        "confidence": 96,
        "match_type": "exact",
        "reason": "Brand and specifications match exactly.",
        "differences": [],
        "manual_review": False,
    }
    result = DeepSeekVerificationResult(**valid_data)
    assert result.is_match is True
    assert result.confidence == 96
    assert result.match_type == "exact"


def test_deepseek_result_schema_invalid():
    invalid_data = {
        "is_match": "not-a-bool",
        "confidence": 150,  # exceeds 100
    }
    with pytest.raises(Exception):
        DeepSeekVerificationResult(**invalid_data)


# ─── Caching & Token Cost Tracking ────────────────────────────────────────────

def test_deepseek_client_caching():
    client_instance = DeepSeekClient()
    az = {"asin": "B08TEST001", "title": "Test Title"}
    sp = {"supplier_name": "Walmart", "supplier_title": "Test Title"}
    cache_key = client_instance.get_cache_key(az, sp)

    # First call
    res1, meta1 = client_instance.verify_product_pair(
        system_prompt="sys",
        user_prompt="user",
        cache_key=cache_key,
    )
    assert res1 is not None
    assert meta1["total_tokens"] > 0
    assert meta1["estimated_cost_usd"] > 0

    # Second call should hit cache
    res2, meta2 = client_instance.verify_product_pair(
        system_prompt="sys",
        user_prompt="user",
        cache_key=cache_key,
    )
    assert res2.confidence == res1.confidence
    assert client_instance._cache[cache_key]["result"] == res1


# ─── Safe Error Fallback ──────────────────────────────────────────────────────

def test_verify_candidate_match_fallback_on_unambiguous():
    az = {"asin": "B08XYZ1001", "title": "Coffee Maker"}
    sp = {"supplier_name": "Walmart", "supplier_title": "Coffee Maker"}
    deterministic = {
        "match_type": "exact",
        "deterministic_score": 100.0,
        "score": 1.0,
        "final_decision": "accepted",
    }
    # Should not call AI because it's not ambiguous
    res = verify_candidate_match(az, sp, deterministic, force=False)
    assert res.get("ai_verified") is False
    assert res["final_decision"] == "accepted"


# ─── On-Demand AI Verification API ────────────────────────────────────────────

def _create_and_wait_demo_scan():
    resp = client.post(
        "/api/scans",
        json={
            "mode": "category",
            "category_config": {
                "category": "Home & Kitchen",
                "max_products": 5,
                "demo": True,
            },
            "demo": True,
        },
        headers=AUTH,
    )
    assert resp.status_code == 201
    scan_id = resp.json()["id"]

    import time
    for _ in range(50):
        prog = client.get(f"/api/scans/{scan_id}/progress", headers=AUTH)
        if prog.json()["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    return scan_id


def test_api_trigger_ai_verification():
    scan_id = _create_and_wait_demo_scan()
    results_resp = client.get(f"/api/scans/{scan_id}/results", headers=AUTH)
    assert results_resp.status_code == 200
    results = results_resp.json()["results"]
    assert len(results) > 0

    target_asin = results[0]["asin"]

    # Call AI verification endpoint
    ai_resp = client.post(
        f"/api/scans/{scan_id}/results/{target_asin}/verify-ai",
        headers=AUTH,
    )
    assert ai_resp.status_code == 200
    item = ai_resp.json()
    assert item["match"]["ai_verified"] is True
    assert item["match"]["ai_score"] is not None
    assert item["match"]["ai_reason"] is not None
    assert item["match"]["tokens_used"] is not None
    assert item["match"]["ai_cost_usd"] is not None


def test_api_trigger_ai_verification_unauthorized():
    scan_id = _create_and_wait_demo_scan()
    resp = client.post(f"/api/scans/{scan_id}/results/B08XYZ1001/verify-ai")
    assert resp.status_code in (401, 403)


def test_api_trigger_ai_verification_wrong_user():
    scan_id = _create_and_wait_demo_scan()
    resp = client.post(
        f"/api/scans/{scan_id}/results/B08XYZ1001/verify-ai",
        headers={"Authorization": "Bearer outsider"},
    )
    assert resp.status_code == 403


def test_api_trigger_ai_verification_not_found():
    scan_id = _create_and_wait_demo_scan()
    resp = client.post(
        f"/api/scans/{scan_id}/results/NONEXISTENT/verify-ai",
        headers=AUTH,
    )
    assert resp.status_code == 404
