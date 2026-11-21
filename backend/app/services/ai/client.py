"""
DeepSeek API Client for Product Verification (Phase 6).

Handles:
  - Selective candidate verification via DeepSeek Chat API
  - Prompt/response hashing and in-memory cache to prevent redundant API calls
  - Robust timeout, retry, and fallback on network/API failure
  - Token tracking and estimated cost calculation
  - Deterministic simulation mode when DEEPSEEK_API_KEY is not configured
"""
import os
import json
import hashlib
import time
from typing import Dict, Any, Optional, Tuple
from loguru import logger
from pydantic import BaseModel, Field

# Pricing per 1,000,000 tokens (DeepSeek-V3 standard rates)
PROMPT_COST_PER_M = 0.14
COMPLETION_COST_PER_M = 0.28


class DeepSeekVerificationResult(BaseModel):
    is_match: bool = Field(..., description="Whether the two listings represent the exact same product")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score from 0 to 100")
    match_type: str = Field(..., description="exact | variant | different_item | uncertain")
    reason: str = Field(..., description="Detailed explanation of the match or mismatch")
    differences: list[str] = Field(default_factory=list, description="List of detected discrepancies")
    manual_review: bool = Field(False, description="Whether human review is recommended")


class DeepSeekClient:
    """Client for DeepSeek Chat API with in-memory caching and safe fallbacks."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_cache_key(self, az_dict: Dict[str, Any], sp_dict: Dict[str, Any], prompt_ver: str = "v1") -> str:
        """Create a deterministic hash fingerprint of the product pair and prompt version."""
        raw = f"{az_dict.get('asin')}:{az_dict.get('title')}:{sp_dict.get('supplier_name')}:{sp_dict.get('supplier_title')}:{prompt_ver}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def verify_product_pair(
        self,
        system_prompt: str,
        user_prompt: str,
        cache_key: Optional[str] = None,
        mock_fallback: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[DeepSeekVerificationResult], Dict[str, Any]]:
        """
        Send structured prompt to DeepSeek and parse result.
        Returns (result, metadata_dict).
        """
        # 1. Check cache
        if cache_key and cache_key in self._cache:
            logger.info(f"DeepSeek AI verification cache hit: {cache_key[:8]}")
            cached = self._cache[cache_key]
            return cached["result"], cached["metadata"]

        # 2. Check if live API key is available
        if not self.api_key or self.api_key.startswith("your_"):
            # Return simulated AI verification
            return self._simulated_ai_response(user_prompt, cache_key, mock_fallback)

        # 3. Call live DeepSeek API with retry and timeout
        import httpx
        metadata = {
            "cached": False,
            "tokens_prompt": 0,
            "tokens_completion": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "latency_ms": 0,
            "model": self.model,
        }

        start_time = time.time()
        for attempt in range(2):
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "response_format": {"type": "json_object"},
                            "temperature": 0.1,
                        },
                    )
                    latency = int((time.time() - start_time) * 1000)
                    metadata["latency_ms"] = latency

                    if resp.status_code == 200:
                        data = resp.json()
                        usage = data.get("usage", {})
                        p_tokens = usage.get("prompt_tokens", 0)
                        c_tokens = usage.get("completion_tokens", 0)
                        metadata["tokens_prompt"] = p_tokens
                        metadata["tokens_completion"] = c_tokens
                        metadata["total_tokens"] = p_tokens + c_tokens
                        metadata["estimated_cost_usd"] = round(
                            (p_tokens / 1_000_000 * PROMPT_COST_PER_M)
                            + (c_tokens / 1_000_000 * COMPLETION_COST_PER_M),
                            6,
                        )

                        content_str = data["choices"][0]["message"]["content"]
                        parsed = json.loads(content_str)
                        verified = DeepSeekVerificationResult(**parsed)

                        if cache_key:
                            self._cache[cache_key] = {"result": verified, "metadata": metadata}
                        return verified, metadata
                    else:
                        logger.warning(f"DeepSeek API HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"DeepSeek call attempt {attempt+1} failed: {e}")
                time.sleep(0.5)

        # Fall back gracefully to simulation if API call fails
        logger.warning("DeepSeek API unreachable; falling back to heuristic evaluation.")
        return self._simulated_ai_response(user_prompt, cache_key, mock_fallback)

    def _simulated_ai_response(
        self,
        user_prompt: str,
        cache_key: Optional[str] = None,
        mock_fallback: Optional[Dict[str, Any]] = None,
    ) -> Tuple[DeepSeekVerificationResult, Dict[str, Any]]:
        """Simulate realistic DeepSeek response based on prompt context."""
        metadata = {
            "cached": False,
            "simulated": True,
            "tokens_prompt": 380,
            "tokens_completion": 65,
            "total_tokens": 445,
            "estimated_cost_usd": 0.000071,
            "latency_ms": 120,
            "model": f"{self.model}-simulated",
        }

        if mock_fallback:
            res = DeepSeekVerificationResult(**mock_fallback)
            if cache_key:
                self._cache[cache_key] = {"result": res, "metadata": metadata}
            return res, metadata

        # Deterministic simulation parsing from prompt
        lower = user_prompt.lower()
        if "pack count discrepancy" in lower or "package quantity" in lower:
            res = DeepSeekVerificationResult(
                is_match=False,
                confidence=72,
                match_type="variant",
                reason="The items share brand and product type, but have conflicting package quantities (e.g. multi-pack vs single).",
                differences=["Package quantity mismatch detected between listings"],
                manual_review=True,
            )
        elif "model number conflict" in lower or "mpn conflict" in lower:
            res = DeepSeekVerificationResult(
                is_match=False,
                confidence=95,
                match_type="different_item",
                reason="The supplier listing has a different model identifier and represents a distinct model variant.",
                differences=["Model number conflict between Amazon and Supplier listings"],
                manual_review=False,
            )
        elif "brand conflict" in lower:
            res = DeepSeekVerificationResult(
                is_match=False,
                confidence=99,
                match_type="different_item",
                reason="Different manufacturers/brands identified on listings.",
                differences=["Brand conflict"],
                manual_review=False,
            )
        else:
            res = DeepSeekVerificationResult(
                is_match=True,
                confidence=92,
                match_type="exact",
                reason="The brand, product title, and core specifications align between Amazon and supplier listings.",
                differences=[],
                manual_review=False,
            )

        if cache_key:
            self._cache[cache_key] = {"result": res, "metadata": metadata}
        return res, metadata
