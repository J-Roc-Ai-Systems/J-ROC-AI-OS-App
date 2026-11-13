"""Gateway and per-worker authentication helpers plus safe audit redaction."""
import re
from fastapi import Header, HTTPException
from .database import db
from .models import utc_now

_SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/-]+=*"),
]

def redact(value: str) -> str:
    cleaned = value
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned[:4000]

def require_platform_access(authorization: str | None = Header(default=None)) -> None:
    from app import require_gateway_token
    require_gateway_token(authorization)

def require_worker_identity(
    worker_id: str,
    authorization: str | None = Header(default=None),
) -> str:
    token = (authorization or "").removeprefix("Bearer ").strip()
    from .workers import workers
    if not workers.authenticate(worker_id, token):
        raise HTTPException(status_code=401, detail="Worker authentication failed.")
    return worker_id

def audit(action: str, resource_type: str, resource_id: str, details: str = "") -> None:
    db.execute("INSERT INTO audit_events(actor,action,resource_type,resource_id,details,created_at) VALUES(?,?,?,?,?,?)",
               ("platform-service", action, resource_type, resource_id, redact(details), utc_now()))
