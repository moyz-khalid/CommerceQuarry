"""
Auth dependency — extracts user_id from a Bearer token.
Phase 3: still a demo placeholder. Phase 10 will verify Supabase JWTs.
"""
import os
from typing import Optional
from fastapi import Depends, HTTPException, Header


async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized — Bearer token required.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty token.")
    # In a real app: verify JWT with Supabase, return sub/user_id claim.
    return token
