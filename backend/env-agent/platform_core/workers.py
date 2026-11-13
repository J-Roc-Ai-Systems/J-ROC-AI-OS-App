"""Durable worker queue with per-worker credentials, leases, recovery and bounded retries."""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from .database import db
from .models import WorkerRegistration, JobSubmission, utc_now
from .security import audit

def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _future(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()

class WorkerService:
    def register(self, item: WorkerRegistration):
        now = utc_now()
        token = secrets.token_urlsafe(36)
        db.execute("""INSERT INTO workers(worker_id,display_name,worker_type,capabilities,max_concurrent_jobs,state,created_at,updated_at,token_hash,last_heartbeat_at)
          VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(worker_id) DO UPDATE SET display_name=excluded.display_name,worker_type=excluded.worker_type,capabilities=excluded.capabilities,max_concurrent_jobs=excluded.max_concurrent_jobs,state='idle',updated_at=excluded.updated_at,token_hash=excluded.token_hash,last_heartbeat_at=excluded.last_heartbeat_at""",
          (item.worker_id,item.display_name,item.worker_type,db.encode(item.capabilities),item.max_concurrent_jobs,"idle",now,now,_hash_token(token),now))
        audit("worker.register", "worker", item.worker_id, "worker credential rotated")
        result = self.get(item.worker_id)
        result["worker_token"] = token
        result["credential_notice"] = "Save this credential in the Environment Agent. It is displayed only once."
        return result

    def authenticate(self, worker_id: str, token: str | None) -> bool:
        if not token:
            return False
        row = db.one("SELECT token_hash FROM workers WHERE worker_id=?", (worker_id,))
        return bool(row and row.get("token_hash") and hmac.compare_digest(row["token_hash"], _hash_token(token)))

    def get(self, worker_id: str):
        row = db.one("SELECT * FROM workers WHERE worker_id=?", (worker_id,))
        if row:
            row["capabilities"] = db.decode(row["capabilities"], [])
            row.pop("token_hash", None)
        return row

    def list(self):
        rows = db.many("SELECT * FROM workers ORDER BY created_at")
        for row in rows:
            row["capabilities"] = db.decode(row["capabilities"], [])
            row.pop("token_hash", None)
        return rows

    def set_state(self, worker_id: str, state: str):
        if state not in {"idle","paused","disabled"}:
            raise ValueError("Unsupported worker state transition")
        changed = db.execute("UPDATE workers SET state=?,updated_at=? WHERE worker_id=?", (state,utc_now(),worker_id))
        if not changed:
            return None
        audit("worker.state", "worker", worker_id, state)
        return self.get(worker_id)

    def submit(self, item: JobSubmission):
        job_id = str(uuid.uuid4())
        now = utc_now()
        db.execute("INSERT INTO jobs(job_id,job_type,payload,priority,required_capability,state,created_at,updated_at,max_attempts) VALUES(?,?,?,?,?,?,?,?,?)",
          (job_id,item.job_type,db.encode(item.payload),item.priority,item.required_capability,"queued",now,now,item.max_attempts))
        audit("job.submit", "job", job_id, item.job_type)
        return self.get_job(job_id)

    def get_job(self, job_id: str):
        row = db.one("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        if row:
            row["payload"] = db.decode(row["payload"], {})
            row["result"] = db.decode(row["result"])
            row.pop("error", None)
            row["cancel_requested"] = bool(row.get("cancel_requested", 0))
        return row

    def list_jobs(self, limit: int = 100):
        rows = db.many("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
        for row in rows:
            row["payload"] = db.decode(row["payload"], {})
            row["result"] = db.decode(row["result"])
            row.pop("error", None)
            row["cancel_requested"] = bool(row.get("cancel_requested", 0))
        return rows

    def recover_expired(self):
        connection = db.connect()
        now = utc_now()
        connection.execute("BEGIN IMMEDIATE")
        try:
            expired = connection.execute("SELECT job_id,assigned_worker,attempts,max_attempts FROM jobs WHERE state='running' AND lease_expires_at IS NOT NULL AND lease_expires_at<?", (now,)).fetchall()
            recovered = []
            for job in expired:
                state = "queued" if job["attempts"] < job["max_attempts"] else "failed"
                connection.execute("UPDATE jobs SET state=?,assigned_worker=NULL,lease_expires_at=NULL,error=?,updated_at=? WHERE job_id=?",
                    (state, "Worker lease expired; job returned to queue." if state == "queued" else "Worker lease expired; retry limit reached.", now, job["job_id"]))
                recovered.append(job["job_id"])
            connection.execute("UPDATE workers SET state='idle',updated_at=? WHERE state='running' AND worker_id NOT IN (SELECT DISTINCT assigned_worker FROM jobs WHERE state='running')", (now,))
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        for job_id in recovered:
            audit("job.lease_recovered", "job", job_id)
        return {"recovered": recovered, "count": len(recovered)}

    def claim(self, worker_id: str, lease_seconds: int = 90):
        self.recover_expired()
        connection = db.connect()
        connection.execute("BEGIN IMMEDIATE")
        try:
            worker_row = connection.execute("SELECT * FROM workers WHERE worker_id=?", (worker_id,)).fetchone()
            if not worker_row or worker_row["state"] in {"paused","disabled"}:
                connection.execute("ROLLBACK")
                return None
            active = connection.execute("SELECT COUNT(*) FROM jobs WHERE assigned_worker=? AND state='running'", (worker_id,)).fetchone()[0]
            if active >= worker_row["max_concurrent_jobs"]:
                connection.execute("ROLLBACK")
                return None
            capabilities = db.decode(worker_row["capabilities"], [])
            candidates = connection.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY priority DESC,created_at ASC LIMIT 100").fetchall()
            row = next((candidate for candidate in candidates if not candidate["required_capability"] or candidate["required_capability"] in capabilities), None)
            if not row:
                connection.execute("ROLLBACK")
                return None
            now = utc_now()
            lease = _future(max(15, min(lease_seconds, 600)))
            connection.execute("UPDATE jobs SET state='running',assigned_worker=?,attempts=attempts+1,lease_expires_at=?,updated_at=? WHERE job_id=? AND state='queued'", (worker_id,lease,now,row["job_id"]))
            connection.execute("UPDATE workers SET state='running',last_heartbeat_at=?,updated_at=? WHERE worker_id=?", (now,now,worker_id))
            connection.execute("COMMIT")
            claimed = dict(row)
            claimed.update(state="running",assigned_worker=worker_id,attempts=row["attempts"]+1,lease_expires_at=lease,updated_at=now)
        except Exception:
            connection.execute("ROLLBACK")
            raise
        claimed["payload"] = db.decode(claimed["payload"], {})
        audit("job.claim", "job", claimed["job_id"], worker_id)
        return claimed

    def heartbeat(self, worker_id: str, lease_seconds: int = 90):
        now = utc_now()
        lease = _future(max(15, min(lease_seconds, 600)))
        connection = db.connect()
        connection.execute("BEGIN IMMEDIATE")
        try:
            worker = connection.execute("SELECT state FROM workers WHERE worker_id=?", (worker_id,)).fetchone()
            if not worker or worker["state"] in {"paused", "disabled"}:
                connection.execute("ROLLBACK")
                return None
            connection.execute("UPDATE workers SET last_heartbeat_at=?,updated_at=? WHERE worker_id=?", (now,now,worker_id))
            connection.execute("UPDATE jobs SET lease_expires_at=?,updated_at=? WHERE assigned_worker=? AND state='running'", (lease,now,worker_id))
            active = connection.execute("SELECT COUNT(*) FROM jobs WHERE assigned_worker=? AND state='running'", (worker_id,)).fetchone()[0]
            connection.execute("UPDATE workers SET state=? WHERE worker_id=?", ("running" if active else "idle",worker_id))
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        return {"worker_id":worker_id,"active_jobs":active,"lease_expires_at":lease}

    def finish(self, job_id: str, worker_id: str, result: dict, error: str | None = None):
        connection = db.connect()
        connection.execute("BEGIN IMMEDIATE")
        try:
            job = connection.execute("SELECT * FROM jobs WHERE job_id=? AND assigned_worker=? AND state='running'", (job_id,worker_id)).fetchone()
            if not job:
                connection.execute("ROLLBACK")
                return None
            state = "failed" if error else "completed"
            safe_error = "[REDACTED]" if error else None
            connection.execute("UPDATE jobs SET state=?,result=?,error=?,lease_expires_at=NULL,updated_at=? WHERE job_id=?", (state,db.encode(result),safe_error,utc_now(),job_id))
            remaining = connection.execute("SELECT COUNT(*) FROM jobs WHERE assigned_worker=? AND state='running'", (worker_id,)).fetchone()[0]
            connection.execute("UPDATE workers SET state=?,updated_at=? WHERE worker_id=?", ("running" if remaining else "idle",utc_now(),worker_id))
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        audit("job."+state, "job", job_id, worker_id)
        return self.get_job(job_id)

    def cancel(self, job_id: str):
        row = db.one("SELECT state FROM jobs WHERE job_id=?", (job_id,))
        if not row or row["state"] in {"completed","failed","cancelled"}:
            return None
        db.execute("UPDATE jobs SET state='cancelled',cancel_requested=1,lease_expires_at=NULL,updated_at=? WHERE job_id=?", (utc_now(),job_id))
        audit("job.cancel", "job", job_id)
        return self.get_job(job_id)

    def retry(self, job_id: str):
        row = db.one("SELECT state,attempts,max_attempts FROM jobs WHERE job_id=?", (job_id,))
        if not row or row["state"] not in {"failed","cancelled"} or row["attempts"] >= row["max_attempts"]:
            return None
        db.execute("UPDATE jobs SET state='queued',assigned_worker=NULL,lease_expires_at=NULL,error=NULL,result=NULL,cancel_requested=0,updated_at=? WHERE job_id=?", (utc_now(),job_id))
        audit("job.retry", "job", job_id)
        return self.get_job(job_id)

workers = WorkerService()
