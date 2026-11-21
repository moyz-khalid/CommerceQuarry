import os
import asyncio
import asyncpg
from pathlib import Path

SQL_PATH = Path(__file__).parent.parent / "database" / "migrations" / "001_initial.sql"

async def run_migration():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set in environment")
    conn = await asyncpg.connect(dsn=db_url)
    try:
        sql = SQL_PATH.read_text()
        await conn.execute(sql)
        print("Migration applied successfully.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_migration())
