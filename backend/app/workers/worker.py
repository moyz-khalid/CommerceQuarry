"""
Celery worker and scan orchestration task.

The `run_scan` task:
  1. Marks the scan as `running`.
  2. Dispatches to the correct sourcing handler (category / seller / product).
  3. For demo mode, calls the demo provider adapter.
  4. Updates progress counters incrementally.
  5. Marks the scan as completed / failed.
"""
import os
import time
from datetime import datetime
from uuid import UUID

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="run_scan", bind=True, max_retries=3)
def run_scan(self, scan_id: str):
    """
    Main scan orchestration task.
    Imports are inside the function to avoid circular-import issues at worker startup.
    """
    from app.services.sourcing.scan_store import get_scan, update_scan
    from app.services.sourcing.orchestrator import orchestrate_scan

    sid = UUID(scan_id)
    scan = get_scan(sid)
    if not scan:
        return {"error": "Scan not found"}

    # Guard: only process queued scans
    if scan.status != "queued":
        return {"error": f"Scan is in state '{scan.status}', not queued."}

    update_scan(sid, status="running")

    try:
        orchestrate_scan(sid)
    except Exception as exc:
        update_scan(
            sid,
            status="failed",
            error_summary=str(exc),
            completed_at=datetime.utcnow(),
        )
        raise self.retry(exc=exc, countdown=10)

    return {"scan_id": scan_id, "status": "completed"}


@celery_app.task(name="ping")
def ping():
    return "pong"
