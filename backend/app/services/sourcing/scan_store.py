"""
In-memory scan store with persistence helpers.
Replaces the flat _scans dict with a proper ScanRecord dataclass.
When a real DB is wired in, replace these functions with SQLAlchemy calls.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, Dict, List, Any
import threading

@dataclass
class ScanRecord:
    id: UUID
    user_id: str
    mode: str
    config: dict
    status: str = "queued"
    progress: int = 0
    total: int = 0
    matched: int = 0
    profitable: int = 0
    error_summary: Optional[str] = None
    demo: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    # Phase 4: persisted result items (one per processed product)
    results: List[Dict[str, Any]] = field(default_factory=list)

_lock = threading.Lock()
_store: Dict[UUID, ScanRecord] = {}


def create_scan(user_id: str, mode: str, config: dict, demo: bool = False) -> ScanRecord:
    scan = ScanRecord(
        id=uuid4(),
        user_id=user_id,
        mode=mode,
        config=config,
        demo=demo,
    )
    with _lock:
        _store[scan.id] = scan
    return scan


def get_scan(scan_id: UUID) -> Optional[ScanRecord]:
    return _store.get(scan_id)


def list_scans(user_id: str):
    return [s for s in _store.values() if s.user_id == user_id]


def update_scan(scan_id: UUID, **kwargs) -> Optional[ScanRecord]:
    with _lock:
        scan = _store.get(scan_id)
        if not scan:
            return None
        for k, v in kwargs.items():
            setattr(scan, k, v)
        scan.updated_at = datetime.utcnow()
        return scan


def cancel_scan(scan_id: UUID) -> Optional[ScanRecord]:
    return update_scan(scan_id, status="cancelled", completed_at=datetime.utcnow())
