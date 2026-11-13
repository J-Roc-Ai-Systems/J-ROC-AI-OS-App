"""Persistent worker registry and durable task queue. Workers poll; jobs are never executed from user input."""
import uuid
from .database import db
from .models import WorkerRegistration, JobSubmission, utc_now
from .security import audit

class WorkerService:
    def register(self, item: WorkerRegistration):
        now = utc_now()
        db.execute("""INSERT INTO workers VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(worker_id) DO UPDATE SET display_name=excluded.display_name,worker_type=excluded.worker_type,capabilities=excluded.capabilities,max_concurrent_jobs=excluded.max_concurrent_jobs,updated_at=excluded.updated_at""",
          (item.worker_id,item.display_name,item.worker_type,db.encode(item.capabilities),item.max_concurrent_jobs,"idle",now,now))
        audit("worker.register", "worker", item.worker_id)
        return self.get(item.worker_id)
    def get(self, worker_id: str):
        row = db.one("SELECT * FROM workers WHERE worker_id=?", (worker_id,))
        if row: row["capabilities"] = db.decode(row["capabilities"], [])
        return row
    def list(self):
        rows = db.many("SELECT * FROM workers ORDER BY created_at")
        for row in rows: row["capabilities"] = db.decode(row["capabilities"], [])
        return rows
    def set_state(self, worker_id: str, state: str):
        if state not in {"idle","paused","disabled"}: raise ValueError("Unsupported worker state transition")
        changed = db.execute("UPDATE workers SET state=?,updated_at=? WHERE worker_id=?", (state,utc_now(),worker_id))
        if not changed: return None
        audit("worker.state", "worker", worker_id, state)
        return self.get(worker_id)
    def submit(self, item: JobSubmission):
        job_id = str(uuid.uuid4()); now = utc_now()
        db.execute("INSERT INTO jobs(job_id,job_type,payload,priority,required_capability,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
          (job_id,item.job_type,db.encode(item.payload),item.priority,item.required_capability,"queued",now,now))
        audit("job.submit", "job", job_id, item.job_type)
        return self.get_job(job_id)
    def get_job(self, job_id: str):
        row = db.one("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        if row: row["payload"] = db.decode(row["payload"], {}); row["result"] = db.decode(row["result"]); row.pop("error", None)
        return row
    def list_jobs(self, limit: int = 100):
        rows = db.many("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        for row in rows: row["payload"] = db.decode(row["payload"], {}); row["result"] = db.decode(row["result"]); row.pop("error", None)
        return rows
    def claim(self, worker_id: str):
        with __import__("contextlib").nullcontext():
            connection = db.connect()
            connection.execute("BEGIN IMMEDIATE")
            try:
                worker_row = connection.execute("SELECT * FROM workers WHERE worker_id=?", (worker_id,)).fetchone()
                if not worker_row or worker_row["state"] in {"paused","disabled"}: connection.execute("ROLLBACK"); return None
                active = connection.execute("SELECT COUNT(*) FROM jobs WHERE assigned_worker=? AND state='running'", (worker_id,)).fetchone()[0]
                if active >= worker_row["max_concurrent_jobs"]: connection.execute("ROLLBACK"); return None
                capabilities = db.decode(worker_row["capabilities"], [])
                row = connection.execute("SELECT * FROM jobs WHERE state='queued' AND (required_capability IS NULL OR required_capability='' OR required_capability IN (SELECT value FROM json_each(?))) ORDER BY priority DESC,created_at ASC LIMIT 1", (db.encode(capabilities),)).fetchone()
                if not row: connection.execute("ROLLBACK"); return None
                now = utc_now()
                connection.execute("UPDATE jobs SET state='running',assigned_worker=?,attempts=attempts+1,updated_at=? WHERE job_id=? AND state='queued'", (worker_id,now,row["job_id"]))
                connection.execute("UPDATE workers SET state='running',updated_at=? WHERE worker_id=?", (now,worker_id))
                connection.execute("COMMIT")
                claimed = dict(row); claimed.update(state="running",assigned_worker=worker_id,attempts=row["attempts"]+1,updated_at=now)
            except Exception:
                connection.execute("ROLLBACK")
                raise
        claimed["payload"] = db.decode(claimed["payload"], {})
        audit("job.claim", "job", claimed["job_id"], worker_id)
        return claimed
    def finish(self, job_id: str, worker_id: str, result: dict, error: str | None = None):
        connection = db.connect()
        connection.execute("BEGIN IMMEDIATE")
        try:
            job = connection.execute("SELECT * FROM jobs WHERE job_id=? AND assigned_worker=? AND state='running'", (job_id,worker_id)).fetchone()
            if not job: connection.execute("ROLLBACK"); return None
            state = "failed" if error else "completed"
            connection.execute("UPDATE jobs SET state=?,result=?,error=?,updated_at=? WHERE job_id=?", (state,db.encode(result),None if not error else "[REDACTED]",utc_now(),job_id))
            remaining = connection.execute("SELECT COUNT(*) FROM jobs WHERE assigned_worker=? AND state='running'", (worker_id,)).fetchone()[0]
            connection.execute("UPDATE workers SET state=?,updated_at=? WHERE worker_id=?", ("running" if remaining else "idle",utc_now(),worker_id))
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        audit("job."+state, "job", job_id, worker_id)
        return self.get_job(job_id)

workers = WorkerService()
