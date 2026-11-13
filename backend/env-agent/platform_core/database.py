"""SQLite persistence with ordered, repeatable schema migrations."""
import json, os, sqlite3, threading
from pathlib import Path
from typing import Any
_LOCK=threading.RLock()
_DEFAULT_PATH=Path(os.getenv("JROCAI_PLATFORM_DATABASE","data/jrocai-platform.sqlite3"))
SCHEMA="""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS workers (worker_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, worker_type TEXT NOT NULL, capabilities TEXT NOT NULL, max_concurrent_jobs INTEGER NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, job_type TEXT NOT NULL, payload TEXT NOT NULL, priority INTEGER NOT NULL, required_capability TEXT, state TEXT NOT NULL, assigned_worker TEXT, attempts INTEGER NOT NULL DEFAULT 0, result TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_jobs_queue ON jobs(state,priority DESC,created_at ASC);
CREATE TABLE IF NOT EXISTS integrations (integration_id TEXT PRIMARY KEY,display_name TEXT NOT NULL,integration_type TEXT NOT NULL,provider TEXT NOT NULL,capabilities TEXT NOT NULL,secret_reference TEXT,state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY,project_name TEXT NOT NULL,project_type TEXT NOT NULL,target_platforms TEXT NOT NULL,description TEXT NOT NULL,state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY,display_name TEXT NOT NULL,device_type TEXT NOT NULL,connection_type TEXT NOT NULL,capabilities TEXT NOT NULL,state TEXT NOT NULL,last_seen TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications (notification_id INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT NOT NULL,title TEXT NOT NULL,message TEXT NOT NULL,severity TEXT NOT NULL,read_at TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS knowledge_documents (document_id TEXT PRIMARY KEY,title TEXT NOT NULL,source_reference TEXT NOT NULL,content TEXT NOT NULL,content_hash TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_knowledge_title ON knowledge_documents(title);
CREATE TABLE IF NOT EXISTS applications (application_id TEXT PRIMARY KEY,display_name TEXT NOT NULL,version TEXT NOT NULL,platform TEXT NOT NULL,package_reference TEXT,state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_events (event_id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,resource_type TEXT NOT NULL,resource_id TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS platform_events (event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,source TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_platform_events_created ON platform_events(created_at);
CREATE TABLE IF NOT EXISTS platform_services (service_id TEXT PRIMARY KEY,display_name TEXT NOT NULL,version TEXT NOT NULL,capabilities TEXT NOT NULL,state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
"""
MIGRATIONS=[
("0001_platform_baseline",SCHEMA),
("0002_worker_identity_and_leases", """
CREATE TABLE IF NOT EXISTS worker_credentials(worker_id TEXT PRIMARY KEY REFERENCES workers(worker_id) ON DELETE CASCADE,token_hash TEXT NOT NULL,created_at TEXT NOT NULL,revoked_at TEXT);
CREATE INDEX IF NOT EXISTS idx_worker_credentials_active ON worker_credentials(worker_id,revoked_at);
ALTER TABLE jobs ADD COLUMN lease_expires_at TEXT;
CREATE INDEX IF NOT EXISTS idx_jobs_lease ON jobs(state,lease_expires_at);
"""),
("0003_identity_workflows_and_repair", """
CREATE TABLE IF NOT EXISTS platform_users(user_id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE COLLATE NOCASE,display_name TEXT NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'member',state TEXT NOT NULL DEFAULT 'active',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS user_sessions(session_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES platform_users(user_id) ON DELETE CASCADE,token_hash TEXT NOT NULL UNIQUE,expires_at TEXT NOT NULL,revoked_at TEXT,created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id,expires_at);
CREATE TABLE IF NOT EXISTS workflow_definitions(workflow_id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,version INTEGER NOT NULL,steps TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS workflow_runs(run_id TEXT PRIMARY KEY,workflow_id TEXT NOT NULL REFERENCES workflow_definitions(workflow_id),state TEXT NOT NULL,input TEXT NOT NULL,output TEXT,error TEXT,started_at TEXT NOT NULL,finished_at TEXT);
CREATE TABLE IF NOT EXISTS workflow_run_steps(step_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES workflow_runs(run_id) ON DELETE CASCADE,step_index INTEGER NOT NULL,step_name TEXT NOT NULL,state TEXT NOT NULL,input TEXT NOT NULL,output TEXT,error TEXT,started_at TEXT,finished_at TEXT,UNIQUE(run_id,step_index));
CREATE INDEX IF NOT EXISTS idx_workflow_runs_state ON workflow_runs(state,started_at);
CREATE TABLE IF NOT EXISTS repair_profiles(profile_id TEXT PRIMARY KEY,manufacturer TEXT NOT NULL,model TEXT NOT NULL,operating_system TEXT NOT NULL,supported_methods TEXT NOT NULL,safety_notes TEXT NOT NULL,source_reference TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS diagnostic_sessions(session_id TEXT PRIMARY KEY,device_id TEXT,profile_id TEXT,issue_summary TEXT NOT NULL,connection_method TEXT NOT NULL,state TEXT NOT NULL,findings TEXT NOT NULL,next_actions TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_diagnostic_sessions_state ON diagnostic_sessions(state,updated_at);
""")]
class PlatformDatabase:
 def __init__(self,path=None): self.path=Path(path) if path else _DEFAULT_PATH; self._connection=None
 def connect(self):
  if self._connection is None:
   with _LOCK:
    if self._connection is None:
     if str(self.path)!=":memory:": self.path.parent.mkdir(parents=True,exist_ok=True)
     self._connection=sqlite3.connect(str(self.path),timeout=15,check_same_thread=False,isolation_level=None)
     self._connection.row_factory=sqlite3.Row; self._connection.execute("PRAGMA foreign_keys=ON")
     if str(self.path)!=":memory:": self._connection.execute("PRAGMA journal_mode=WAL")
     self.migrate()
  return self._connection
 def migrate(self):
  con=self._connection
  con.execute("CREATE TABLE IF NOT EXISTS schema_migrations(migration_id TEXT PRIMARY KEY,applied_at TEXT NOT NULL)")
  applied={r[0] for r in con.execute("SELECT migration_id FROM schema_migrations")}
  from datetime import datetime,timezone
  for migration_id,script in MIGRATIONS:
   if migration_id in applied: continue
   try:
    con.executescript("BEGIN IMMEDIATE;\n"+script)
    con.execute("INSERT INTO schema_migrations(migration_id,applied_at) VALUES(?,?)",(migration_id,datetime.now(timezone.utc).isoformat()))
    con.execute("COMMIT")
   except Exception:
    if con.in_transaction: con.execute("ROLLBACK")
    raise
 def execute(self,sql,values=()):
  with _LOCK:
   cur=self.connect().execute(sql,values); return cur.lastrowid or cur.rowcount
 def one(self,sql,values=()):
  with _LOCK:
   row=self.connect().execute(sql,values).fetchone(); return dict(row) if row else None
 def many(self,sql,values=()):
  with _LOCK: return [dict(r) for r in self.connect().execute(sql,values).fetchall()]
 @staticmethod
 def encode(value): return json.dumps(value,separators=(",",":"),ensure_ascii=False)
 @staticmethod
 def decode(value,fallback=None):
  if value is None:return fallback
  try:return json.loads(value)
  except (TypeError,json.JSONDecodeError):return fallback
db=PlatformDatabase()
