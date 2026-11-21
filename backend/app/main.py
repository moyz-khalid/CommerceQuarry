import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .api import health_router, scans_router, fee_profiles_router, integrations_router, settings_router
from .init_db import run_migration
from .logger import configure_logger

load_dotenv()
logger = configure_logger()

app = FastAPI(title="CommerceQuarry API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(scans_router, prefix="/api", tags=["Scans"])
app.include_router(fee_profiles_router, prefix="/api", tags=["Fee Profiles"])
app.include_router(integrations_router, prefix="/api", tags=["Integrations"])
app.include_router(settings_router, prefix="/api", tags=["Settings"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    try:
        await run_migration()
    except Exception as e:
        logger.error(f"Migration error: {e}")
