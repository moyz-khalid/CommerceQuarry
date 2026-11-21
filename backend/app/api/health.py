import os
from fastapi import APIRouter

import asyncpg
import redis.asyncio as aioredis
from ..database import DATABASE_URL

router = APIRouter()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/status")
async def status_check():
    # Database check
    db_status = "in-memory (active)"
    if os.getenv("DATABASE_URL"):
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
            db_status = "connected (postgres)"
        except Exception:
            db_status = "error (unreachable)"

    # Redis / Queue check
    redis_status = "local worker queue (active)"
    if os.getenv("REDIS_URL"):
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = aioredis.from_url(redis_url)
            await r.ping()
            redis_status = "connected (redis)"
        except Exception:
            redis_status = "fallback (local thread pool)"

    return {"database": db_status, "redis": redis_status}
