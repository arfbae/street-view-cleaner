from __future__ import annotations
import json, sqlite3, threading, time
from pathlib import Path
from .config import settings

class SQLiteJobStore:
    """Small WAL-backed state cache and durable processing queue metadata."""
    def __init__(self, path: Path):
        self.path=path; self.path.parent.mkdir(parents=True,exist_ok=True); self._lock=threading.Lock(); self._init()
    def _connect(self):
        conn=sqlite3.connect(self.path, timeout=30); conn.row_factory=sqlite3.Row; return conn
    def _init(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, status TEXT NOT NULL, provider TEXT, preset TEXT, payload TEXT, created_at REAL NOT NULL, updated_at REAL NOT NULL)")
            conn.commit()
    def enqueue(self, job_id, provider, preset): self.set(job_id,"queued",provider,preset,{})
    def set(self, job_id, status, provider=None, preset=None, payload=None):
        now=time.time(); payload=json.dumps(payload or {})
        with self._lock, self._connect() as conn:
            conn.execute("INSERT INTO jobs(job_id,status,provider,preset,payload,created_at,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET status=excluded.status, provider=COALESCE(excluded.provider,jobs.provider), preset=excluded.preset, payload=excluded.payload, updated_at=excluded.updated_at",(job_id,status,provider,preset,payload,now,now)); conn.commit()
    def get(self, job_id):
        with self._connect() as conn:
            row=conn.execute("SELECT job_id,status,provider,preset,payload,created_at,updated_at FROM jobs WHERE job_id=?",(job_id,)).fetchone()
        if not row: return None
        return {**dict(row),"payload":json.loads(row["payload"] or "{}") }

store=SQLiteJobStore(settings.storage_root/"state"/"street_view_cleaner.sqlite3")
