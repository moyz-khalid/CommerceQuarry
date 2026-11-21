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
    db_status = "unknown"
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        db_status = "ok"
    except Exception:
        db_status = "error"
    # Redis check
    redis_status = "unknown"
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = aioredis.from_url(redis_url)
        await r.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "error"
    return {"database": db_status, "redis": redis_status}
