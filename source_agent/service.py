from __future__ import annotations
import json
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from .github_client import GitHubApiError, GitHubReadClient

AGENTS = [
    {"agent_id":"source-agent","name":"J-ROC AI Source Agent","description":"Platform-wide repository intelligence and controlled source coordination.","permissions":["repository.read","source.propose","build.request"]},
    {"agent_id":"android-agent","name":"Android Engineering Agent","description":"Android SDK, Kotlin, Gradle, application architecture, and test coordination.","permissions":["repository.read","source.propose","build.request"]},
    {"agent_id":"environment-agent","name":"Environment and Secrets Agent","description":"Environment configuration inventory and secret references; never returns secret values.","permissions":["environment.inspect","secret.reference"]},
    {"agent_id":"test-agent","name":"Quality and Test Agent","description":"Test planning, test result review, and build verification.","permissions":["repository.read","build.request"]},
    {"agent_id":"security-agent","name":"Security Agent","description":"Permission review, dependency risk review, and security gate enforcement.","permissions":["repository.read","security.review"]},
    {"agent_id":"documentation-agent","name":"Documentation Agent","description":"Architecture, API, reusable component, and release documentation.","permissions":["repository.read","documentation.propose"]},
]
APPROVAL_TASK_TYPES={"source.write","build.execute","release.publish","dependency.install"}
VALID_TASK_TYPES={"repository.inspect","source.propose","source.write","build.request","build.execute","test.run","dependency.review","dependency.install","documentation.update","security.review","release.publish"}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

class AgentStore:
    def __init__(self, database_path):
        self.database_path=database_path
        Path(database_path).parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, task_type TEXT NOT NULL,
                repository TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL,
                requires_approval INTEGER NOT NULL, approved_by TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, event_type TEXT NOT NULL,
                actor TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL)""")

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.database_path,timeout=10)
        db.row_factory=sqlite3.Row
        try:
            yield db
        finally:
            db.close()

    def create_task(self,payload):
        agent_id=str(payload.get("agent_id","source-agent")).strip()
        task_type=str(payload.get("task_type","")).strip()
        repository=str(payload.get("repository","")).strip()
        description=str(payload.get("description","")).strip()
        if agent_id not in {a["agent_id"] for a in AGENTS}: raise ValueError("Unknown agent_id")
        if task_type not in VALID_TASK_TYPES: raise ValueError("Unsupported task_type")
        if not repository or len(repository)>300 or not description or len(description)>8000:
            raise ValueError("repository and description are required and must be within size limits")
        approval=task_type in APPROVAL_TASK_TYPES
        task_id,now=str(uuid.uuid4()),utc_now()
        status="pending_approval" if approval else "queued"
        with self.connect() as db:
            db.execute("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
                (task_id,agent_id,task_type,repository,description,status,int(approval),now,now))
            self.audit(db,task_id,"task.created","authenticated-user",{"status":status})
        return self.get_task(task_id)

    def get_task(self,task_id):
        with self.connect() as db:
            row=db.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            return dict(row) if row else None

    def approve(self,task_id,approved,actor):
        now=utc_now()
        with self.connect() as db:
            row=db.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if row is None: return None
            if row["status"]!="pending_approval": raise ValueError("Task is not awaiting approval")
            status="queued" if approved else "rejected"
            db.execute("UPDATE tasks SET status=?,approved_by=?,updated_at=? WHERE task_id=?",
                       (status,actor,now,task_id))
            self.audit(db,task_id,"task.approval",actor,{"approved":approved,"status":status})
        return self.get_task(task_id)

    @staticmethod
    def audit(db,task_id,event_type,actor,details):
        db.execute("INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()),task_id,event_type,actor,json.dumps(details),utc_now()))

def make_handler(store,expected_token):
    class Handler(BaseHTTPRequestHandler):
        server_version="JROCAISourceAgent/0.1"
        def send_json(self,status,payload):
            data=json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(data)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(data)

        def authenticated(self):
            header=self.headers.get("Authorization","")
            token=header[7:] if header.startswith("Bearer ") else ""
            return bool(expected_token) and secrets.compare_digest(token,expected_token)

        def read_json(self):
            length=int(self.headers.get("Content-Length","0"))
            if length<2 or length>16384: raise ValueError("Body must be between 2 and 16384 bytes")
            payload=json.loads(self.rfile.read(length))
            if not isinstance(payload,dict): raise ValueError("JSON body must be an object")
            return payload

        def do_GET(self):
            path=urlparse(self.path).path
            if path=="/health":
                self.send_json(200,{"status":"ok","service":"jrocai-source-agent","version":"0.1.0"})
                return
            if not self.authenticated():
                self.send_json(401,{"error":"unauthorized","message":"A valid bearer token is required"})
                return
            if path=="/v1/agents":
                self.send_json(200,{"agents":AGENTS})
                return
            if path.startswith("/v1/tasks/"):
                task=store.get_task(path.rsplit("/",1)[-1])
                self.send_json(200 if task else 404,task or {"error":"not_found"})
                return
            self.send_json(404,{"error":"not_found"})

        def do_POST(self):
            path=urlparse(self.path).path
            if not self.authenticated():
                self.send_json(401,{"error":"unauthorized","message":"A valid bearer token is required"})
                return
            try:
                payload=self.read_json()
                if path=="/v1/tasks":
                    self.send_json(202,store.create_task(payload))
                    return
                if path.startswith("/v1/tasks/") and path.endswith("/approve"):
                    task_id=path.split("/")[-2]
                    task=store.approve(task_id,payload.get("approved") is True,
                        str(payload.get("actor","platform-owner"))[:120])
                    self.send_json(200 if task else 404,task or {"error":"not_found"})
                    return
                self.send_json(404,{"error":"not_found"})
            except (ValueError,json.JSONDecodeError) as exc:
                self.send_json(400,{"error":"invalid_request","message":str(exc)})

        def log_message(self,format,*args):
            return
    return Handler

def main():
    host=os.environ.get("JROC_SOURCE_AGENT_HOST","127.0.0.1")
    port=int(os.environ.get("JROC_SOURCE_AGENT_PORT","8788"))
    database=os.environ.get("JROC_SOURCE_AGENT_DATABASE","data/source-agent.sqlite3")
    token=os.environ.get("JROC_SOURCE_AGENT_TOKEN","")
    if len(token)<32: raise SystemExit("Set JROC_SOURCE_AGENT_TOKEN to a random value of at least 32 characters.")
    server=ThreadingHTTPServer((host,port),make_handler(AgentStore(database),token))
    print(f"J-ROC AI Source Agent listening on {host}:{port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__":
    main()
