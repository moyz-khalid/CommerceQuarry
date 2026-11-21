"""
AI Verification Package.
"""
from .client import DeepSeekClient, DeepSeekVerificationResult
from .verifier import should_verify_with_ai, build_ai_prompt, verify_candidate_match

__all__ = [
    "DeepSeekClient",
    "DeepSeekVerificationResult",
    "should_verify_with_ai",
    "build_ai_prompt",
    "verify_candidate_match",
]
