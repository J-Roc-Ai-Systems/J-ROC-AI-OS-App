"""Authenticated API for Wave Two services. Single-gateway access is not multi-user identity."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from .security import require_platform_access
from .models import WorkerRegistration, JobSubmission, IntegrationRegistration, ProjectCreate, DeviceRegistration, ApplicationRegistration
from .workers import workers
from .integrations import integrations
from .factory import factory
from .devices import devices
from .knowledge import knowledge
from .communications import communications
from .applications import applications
from .database import db
from .brain import brain, BrainPlanRequest
from .events import events
from .storage import storage

router=APIRouter(prefix="/platform/v1",tags=["J-ROC AI Platform"],dependencies=[Depends(require_platform_access)])
class JobFinish(BaseModel):
    worker_id: str = Field(min_length=2,max_length=80)
    result: dict = Field(default_factory=dict)
    error: str | None = Field(default=None,max_length=1000)
class KnowledgeInput(BaseModel):
    title: str = Field(min_length=1,max_length=240)
    source_reference: str = Field(min_length=1,max_length=500)
    content: str = Field(min_length=1,max_length=100000)
class ServiceRegistration(BaseModel):
    service_id: str = Field(min_length=2,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str = Field(min_length=2,max_length=120)
    version: str = Field(min_length=1,max_length=40)
    capabilities: list[str] = Field(default_factory=list,max_length=40)
class EventInput(BaseModel):
    event_type: str = Field(min_length=2,max_length=100)
    source: str = Field(min_length=2,max_length=100)
    payload: dict = Field(default_factory=dict)
class NotificationInput(BaseModel):
    category: str = Field(min_length=1,max_length=60)
    title: str = Field(min_length=1,max_length=160)
    message: str = Field(min_length=1,max_length=2000)
    severity: str = "info"
class LeaseRequest(BaseModel):
    lease_seconds: int = Field(default=90, ge=15, le=600)

def require_worker(worker_id: str, worker_token: str | None):
    if not workers.authenticate(worker_id, worker_token):
        raise HTTPException(401, "Worker credential is missing or invalid.")

@router.get("/status")
def status():
    migrations=db.many("SELECT version,name,applied_at FROM schema_migrations ORDER BY version")
    return {"service":"jrocai-platform-core","database":"connected","mode":"single-gateway","spending_policy":"cloud_spending_disabled_by_default","schema_version":max((row["version"] for row in migrations),default=0),"migrations":migrations,"modules":["application_factory","brain_foundation","integration_registry","production_workers","device_inventory","platform_registry","communications","knowledge","file_storage_metadata","application_inventory"]}

@router.post("/workers")
def register_worker(item:WorkerRegistration): return workers.register(item)
@router.get("/workers")
def list_workers(): return workers.list()
@router.patch("/workers/{worker_id}/{state}")
def set_worker_state(worker_id:str,state:str):
    try: result=workers.set_state(worker_id,state)
    except ValueError as exc: raise HTTPException(400,str(exc))
    if not result: raise HTTPException(404,"Worker not found")
    return result
@router.post("/jobs")
def submit_job(item:JobSubmission): return workers.submit(item)
@router.get("/jobs")
def list_jobs(limit:int=Query(default=100,ge=1,le=200)): return workers.list_jobs(limit)
@router.post("/workers/{worker_id}/claim")
def claim_job(worker_id:str, lease:LeaseRequest, x_worker_token:str|None=Header(default=None)):
    require_worker(worker_id,x_worker_token)
    return {"job":workers.claim(worker_id,lease.lease_seconds)}
@router.post("/workers/{worker_id}/heartbeat")
def worker_heartbeat(worker_id:str, lease:LeaseRequest, x_worker_token:str|None=Header(default=None)):
    require_worker(worker_id,x_worker_token)
    result=workers.heartbeat(worker_id,lease.lease_seconds)
    if not result: raise HTTPException(409,"Worker is unavailable or disabled.")
    return result
@router.post("/jobs/{job_id}/finish")
def finish_job(job_id:str,payload:JobFinish,x_worker_token:str|None=Header(default=None)):
    require_worker(payload.worker_id,x_worker_token)
    result=workers.finish(job_id,payload.worker_id,payload.result,payload.error)
    if not result: raise HTTPException(409,"Job is not running for this worker")
    return result
@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id:str):
    result=workers.cancel(job_id)
    if not result: raise HTTPException(409,"Job cannot be cancelled in its current state.")
    return result
@router.post("/jobs/{job_id}/retry")
def retry_job(job_id:str):
    result=workers.retry(job_id)
    if not result: raise HTTPException(409,"Job has no retry remaining or is not retryable.")
    return result
@router.post("/jobs/recover-expired")
def recover_expired_jobs(): return workers.recover_expired()

@router.post("/integrations")
def register_integration(item:IntegrationRegistration):
    try: return integrations.register(item)
    except ValueError as exc: raise HTTPException(400,str(exc))
@router.get("/integrations")
def list_integrations(): return integrations.list()
@router.patch("/integrations/{integration_id}/{state}")
def integration_state(integration_id:str,state:str):
    try: result=integrations.set_state(integration_id,state)
    except ValueError as exc: raise HTTPException(400,str(exc))
    if not result: raise HTTPException(404,"Integration not found")
    return result

@router.post("/projects")
def create_project(item:ProjectCreate): return factory.create(item)
@router.get("/projects")
def list_projects(): return factory.list()
@router.post("/projects/{project_id}/prepare-workspace")
def prepare_workspace(project_id:str):
    try: result=factory.prepare_workspace(project_id)
    except FileExistsError: raise HTTPException(409,"Workspace already exists")
    except ValueError as exc: raise HTTPException(400,str(exc))
    if not result: raise HTTPException(404,"Project not found")
    return result

@router.post("/devices")
def register_device(item:DeviceRegistration): return devices.register(item)
@router.get("/devices")
def list_devices(): return devices.list()
@router.patch("/devices/{device_id}/{state}")
def device_state(device_id:str,state:str):
    try: result=devices.set_state(device_id,state)
    except ValueError as exc: raise HTTPException(400,str(exc))
    if not result: raise HTTPException(404,"Device not found")
    return result

@router.post("/knowledge")
def add_knowledge(item:KnowledgeInput): return knowledge.add(item.title,item.source_reference,item.content)
@router.get("/knowledge/search")
def search_knowledge(q:str=Query(min_length=2,max_length=200),limit:int=20): return knowledge.search(q,limit)
@router.post("/notifications")
def publish_notification(item:NotificationInput):
    try: return communications.publish(item.category,item.title,item.message,item.severity)
    except ValueError as exc: raise HTTPException(400,str(exc))
@router.get("/notifications")
def list_notifications(unread_only:bool=False,limit:int=100): return communications.list(unread_only,limit)
@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id:int):
    result=communications.mark_read(notification_id)
    if not result: raise HTTPException(404,"Notification not found")
    return result

@router.post("/applications")
def register_application(item:ApplicationRegistration): return applications.register(item)
@router.get("/applications")
def list_applications(): return applications.list()
@router.get("/audit")
def list_audit(limit:int=Query(default=100,ge=1,le=500)):
    return db.many("SELECT event_id,actor,action,resource_type,resource_id,details,created_at FROM audit_events ORDER BY event_id DESC LIMIT ?",(limit,))

@router.get("/brain/status")
def brain_status(): return brain.status()
@router.post("/brain/plan")
def create_brain_plan(item:BrainPlanRequest): return brain.plan(item)

@router.post("/services")
def register_service(item:ServiceRegistration): return events.register_service(item.service_id,item.display_name,item.version,item.capabilities)
@router.get("/services")
def list_services(): return events.services()
@router.post("/events")
def publish_event(item:EventInput): return events.publish(item.event_type,item.source,item.payload)
@router.get("/events")
def list_events(limit:int=Query(default=100,ge=1,le=500)): return events.list(limit)

@router.get("/files")
def list_files(directory:str="",limit:int=Query(default=200,ge=1,le=500)):
    try: return storage.list(directory,limit)
    except ValueError as exc: raise HTTPException(400,str(exc))
@router.get("/files/metadata")
def file_metadata(path:str=Query(min_length=1,max_length=1000)):
    try: result=storage.metadata(path)
    except ValueError as exc: raise HTTPException(400,str(exc))
    if not result: raise HTTPException(404,"File not found")
    return result
