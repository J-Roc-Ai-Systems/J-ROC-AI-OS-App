"""Persistent worker registry with individual credentials and bounded job leases."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from .database import db
from .models import WorkerRegistration, JobSubmission, utc_now
from .security import audit

LEASE_SECONDS = 120

class WorkerService:
    def register(self, item: WorkerRegistration):
        now = utc_now()
        db.execute("""INSERT INTO workers VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(worker_id) DO UPDATE SET display_name=excluded.display_name,worker_type=excluded.worker_type,capabilities=excluded.capabilities,max_concurrent_jobs=excluded.max_concurrent_jobs,updated_at=excluded.updated_at""",
          (item.worker_id,item.display_name,item.worker_type,db.encode(item.capabilities),item.max_concurrent_jobs,"idle",now,now))
        token = secrets.token_urlsafe(40)
        db.execute("""INSERT INTO worker_credentials(worker_id,token_hash,created_at,revoked_at)
            VALUES(?,?,?,NULL) ON CONFLICT(worker_id) DO UPDATE SET token_hash=excluded.token_hash,created_at=excluded.created_at,revoked_at=NULL""",
            (item.worker_id,hashlib.sha256(token.encode()).hexdigest(),now))
        audit("worker.register", "worker", item.worker_id)
        return {"worker": self.get(item.worker_id), "worker_token": token,
                "token_notice": "Store this token in the Environment Agent secret store. It is shown once."}

    def authenticate(self, worker_id: str, token: str) -> bool:
        row = db.one("SELECT token_hash,revoked_at FROM worker_credentials WHERE worker_id=?", (worker_id,))
        if not row or row["revoked_at"] or not token:
            return False
        return secrets.compare_digest(row["token_hash"], hashlib.sha256(token.encode()).hexdigest())

    def revoke(self, worker_id: str):
        db.execute("UPDATE worker_credentials SET revoked_at=? WHERE worker_id=?", (utc_now(),worker_id))
        audit("worker.credential.revoke","worker",worker_id)

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
        if state in {"paused","disabled"}:
            self.revoke(worker_id)
        audit("worker.state", "worker", worker_id, state)
        return self.get(worker_id)

    def heartbeat(self, worker_id: str):
        worker = self.get(worker_id)
        if not worker or worker["state"] in {"paused","disabled"}:
            return None
        db.execute("UPDATE workers SET updated_at=? WHERE worker_id=?", (utc_now(),worker_id))
        audit("worker.heartbeat","worker",worker_id)
        return {"worker_id":worker_id,"state":worker["state"],"received_at":utc_now()}

    def renew_lease(self, job_id: str, worker_id: str):
        now = datetime.now(timezone.utc)
        connection = db.connect()
        connection.execute("BEGIN IMMEDIATE")
        try:
            job = connection.execute("SELECT state,lease_expires_at FROM jobs WHERE job_id=? AND assigned_worker=?", (job_id,worker_id)).fetchone()
            if not job or job["state"] != "running":
                connection.execute("ROLLBACK")
                return None
            if job["lease_expires_at"] and job["lease_expires_at"] < now.isoformat():
                connection.execute("ROLLBACK")
                return None
            expires = (now + timedelta(seconds=LEASE_SECONDS)).isoformat()
            connection.execute("UPDATE jobs SET lease_expires_at=?,updated_at=? WHERE job_id=?", (expires,now.isoformat(),job_id))
            connection.execute("UPDATE workers SET updated_at=? WHERE worker_id=?", (now.isoformat(),worker_id))
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        audit("job.lease.renew","job",job_id,worker_id)
        return {"job_id":job_id,"worker_id":worker_id,"lease_expires_at":expires}

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

    def recover_expired_leases(self):
        now = utc_now()
        connection = db.connect()
        connection.execute("BEGIN IMMEDIATE")
        try:
            expired = connection.execute("SELECT job_id,assigned_worker FROM jobs WHERE state='running' AND lease_expires_at IS NOT NULL AND lease_expires_at<?", (now,)).fetchall()
            for job in expired:
                connection.execute("UPDATE jobs SET state='queued',assigned_worker=NULL,lease_expires_at=NULL,updated_at=? WHERE job_id=?", (now,job["job_id"]))
                connection.execute("UPDATE workers SET state='idle',updated_at=? WHERE worker_id=? AND NOT EXISTS (SELECT 1 FROM jobs WHERE assigned_worker=? AND state='running')", (now,job["assigned_worker"],job["assigned_worker"]))
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        for job in expired:
            audit("job.lease_expired","job",job["job_id"],job["assigned_worker"] or "")
        return len(expired)

    def claim(self, worker_id: str):
        self.recover_expired_leases()
        connection = db.connect()
        connection.execute("BEGIN IMMEDIATE")
        try:
            worker_row = connection.execute("SELECT * FROM workers WHERE worker_id=?", (worker_id,)).fetchone()
            if not worker_row or worker_row["state"] in {"paused","disabled"}:
                connection.execute("ROLLBACK"); return None
            active = connection.execute("SELECT COUNT(*) FROM jobs WHERE assigned_worker=? AND state='running'", (worker_id,)).fetchone()[0]
            if active >= worker_row["max_concurrent_jobs"]:
                connection.execute("ROLLBACK"); return None
            capabilities = db.decode(worker_row["capabilities"], [])
            row = connection.execute("""SELECT * FROM jobs WHERE state='queued'
                AND (required_capability IS NULL OR required_capability=''
                OR required_capability IN (SELECT value FROM json_each(?)))
                ORDER BY priority DESC,created_at ASC LIMIT 1""", (db.encode(capabilities),)).fetchone()
            if not row:
                connection.execute("ROLLBACK"); return None
            now = datetime.now(timezone.utc)
            now_text = now.isoformat()
            expires = (now + timedelta(seconds=LEASE_SECONDS)).isoformat()
            connection.execute("UPDATE jobs SET state='running',assigned_worker=?,attempts=attempts+1,lease_expires_at=?,updated_at=? WHERE job_id=? AND state='queued'", (worker_id,expires,now_text,row["job_id"]))
            connection.execute("UPDATE workers SET state='running',updated_at=? WHERE worker_id=?", (now_text,worker_id))
            connection.execute("COMMIT")
            claimed = dict(row); claimed.update(state="running",assigned_worker=worker_id,attempts=row["attempts"]+1,lease_expires_at=expires,updated_at=now_text)
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
            if not job:
                connection.execute("ROLLBACK"); return None
            state = "failed" if error else "completed"
            job_payload = db.decode(job["payload"], {})
            connection.execute("UPDATE jobs SET state=?,result=?,error=?,lease_expires_at=NULL,updated_at=? WHERE job_id=?", (state,db.encode(result),None if not error else "[REDACTED]",utc_now(),job_id))
            if job["job_type"] == "build.execute" and job_payload.get("build_run_id"):
                reported_state = "failed" if error else "worker_reported_completed"
                connection.execute("UPDATE build_runs SET state=?,result=?,updated_at=? WHERE run_id=?",
                    (reported_state,db.encode(result),utc_now(),job_payload["build_run_id"]))
            remaining = connection.execute("SELECT COUNT(*) FROM jobs WHERE assigned_worker=? AND state='running'", (worker_id,)).fetchone()[0]
            connection.execute("UPDATE workers SET state=?,updated_at=? WHERE worker_id=?", ("running" if remaining else "idle",utc_now(),worker_id))
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
        audit("job."+state, "job", job_id, worker_id)
        return self.get_job(job_id)

workers = WorkerService()
