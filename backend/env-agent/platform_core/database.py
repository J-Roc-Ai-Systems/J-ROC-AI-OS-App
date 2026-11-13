"""SQLite persistence with additive, versioned migrations for the local-first platform."""
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

_LOCK = threading.RLock()
_DEFAULT_PATH = Path(os.getenv("JROCAI_PLATFORM_DATABASE", "data/jrocai-platform.sqlite3"))
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS workers (worker_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, worker_type TEXT NOT NULL, capabilities TEXT NOT NULL, max_concurrent_jobs INTEGER NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, job_type TEXT NOT NULL, payload TEXT NOT NULL, priority INTEGER NOT NULL, required_capability TEXT, state TEXT NOT NULL, assigned_worker TEXT, attempts INTEGER NOT NULL DEFAULT 0, result TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_jobs_queue ON jobs(state, priority DESC, created_at ASC);
CREATE TABLE IF NOT EXISTS integrations (integration_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, integration_type TEXT NOT NULL, provider TEXT NOT NULL, capabilities TEXT NOT NULL, secret_reference TEXT, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, project_name TEXT NOT NULL, project_type TEXT NOT NULL, target_platforms TEXT NOT NULL, description TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, device_type TEXT NOT NULL, connection_type TEXT NOT NULL, capabilities TEXT NOT NULL, state TEXT NOT NULL, last_seen TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications (notification_id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, title TEXT NOT NULL, message TEXT NOT NULL, severity TEXT NOT NULL, read_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS knowledge_documents (document_id TEXT PRIMARY KEY, title TEXT NOT NULL, source_reference TEXT NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_knowledge_title ON knowledge_documents(title);
CREATE TABLE IF NOT EXISTS applications (application_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, version TEXT NOT NULL, platform TEXT NOT NULL, package_reference TEXT, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_events (event_id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL, action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS platform_events (event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, source TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_platform_events_created ON platform_events(created_at);
CREATE TABLE IF NOT EXISTS platform_services (service_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, version TEXT NOT NULL, capabilities TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
"""

MIGRATIONS = [
    (1, "worker credentials and leased jobs", [
        "ALTER TABLE workers ADD COLUMN token_hash TEXT",
        "ALTER TABLE workers ADD COLUMN last_heartbeat_at TEXT",
        "ALTER TABLE jobs ADD COLUMN lease_expires_at TEXT",
        "ALTER TABLE jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3",
        "ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0",
    ]),
]

class PlatformDatabase:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else _DEFAULT_PATH
        self._connection = None

    def connect(self):
        if self._connection is None:
            with _LOCK:
                if self._connection is None:
                    if str(self.path) != ":memory:":
                        self.path.parent.mkdir(parents=True, exist_ok=True)
                    self._connection = sqlite3.connect(str(self.path), timeout=15, check_same_thread=False, isolation_level=None)
                    self._connection.row_factory = sqlite3.Row
                    self._connection.execute("PRAGMA foreign_keys=ON")
                    if str(self.path) != ":memory:":
                        self._connection.execute("PRAGMA journal_mode=WAL")
                    self._connection.executescript(SCHEMA)
                    self._run_migrations(self._connection)
        return self._connection

    @staticmethod
    def _run_migrations(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
        import datetime
        for version, name, statements in MIGRATIONS:
            if connection.execute("SELECT 1 FROM schema_migrations WHERE version=?", (version,)).fetchone():
                continue
            connection.execute("BEGIN IMMEDIATE")
            try:
                for statement in statements:
                    try:
                        connection.execute(statement)
                    except sqlite3.OperationalError as exc:
                        # An interrupted/legacy rollout may already have applied a column.
                        if "duplicate column name" not in str(exc).lower():
                            raise
                connection.execute(
                    "INSERT INTO schema_migrations(version,name,applied_at) VALUES(?,?,?)",
                    (version, name, datetime.datetime.now(datetime.timezone.utc).isoformat()),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def execute(self, sql: str, values: tuple = ()) -> int:
        with _LOCK:
            cursor = self.connect().execute(sql, values)
            return cursor.lastrowid or cursor.rowcount

    def one(self, sql: str, values: tuple = ()) -> dict[str, Any] | None:
        with _LOCK:
            row = self.connect().execute(sql, values).fetchone()
            return dict(row) if row else None

    def many(self, sql: str, values: tuple = ()) -> list[dict[str, Any]]:
        with _LOCK:
            return [dict(row) for row in self.connect().execute(sql, values).fetchall()]

    @staticmethod
    def encode(value: Any) -> str:
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def decode(value: str | None, fallback: Any = None) -> Any:
        if value is None:
            return fallback
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return fallback

db = PlatformDatabase()
