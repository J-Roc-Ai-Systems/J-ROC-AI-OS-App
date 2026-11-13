"""Authenticated administrator and separately authenticated worker APIs."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from .security import require_platform_access, require_worker_identity
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
worker_router=APIRouter(prefix="/platform/v1",tags=["J-ROC AI Workers"])
class JobFinish(BaseModel):
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

@router.get("/status")
def status():
    return {"service":"jrocai-platform-core","database":"connected","mode":"gateway-admin-plus-worker-identities","spending_policy":"cloud_spending_disabled_by_default","modules":["application_factory","brain_foundation","integration_registry","production_workers","device_inventory","platform_registry","communications","knowledge","file_storage_metadata","application_inventory"]}

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
@router.delete("/workers/{worker_id}/credential")
def revoke_worker_credential(worker_id:str):
    if not workers.get(worker_id): raise HTTPException(404,"Worker not found")
    workers.revoke(worker_id)
    return {"worker_id":worker_id,"credential_state":"revoked"}

@router.post("/jobs")
def submit_job(item:JobSubmission): return workers.submit(item)
@router.get("/jobs")
def list_jobs(limit:int=Query(default=100,ge=1,le=200)): return workers.list_jobs(limit)

@worker_router.post("/workers/{worker_id}/heartbeat")
def worker_heartbeat(worker_id:str, authenticated_worker:str=Depends(require_worker_identity)):
    if authenticated_worker != worker_id: raise HTTPException(403,"Worker identity mismatch")
    result=workers.heartbeat(authenticated_worker)
    if not result: raise HTTPException(403,"Worker is paused, disabled or unknown")
    return result

@worker_router.post("/jobs/{job_id}/heartbeat")
def renew_job_lease(job_id:str, worker_id:str=Query(min_length=2,max_length=80), authenticated_worker:str=Depends(require_worker_identity)):
    if authenticated_worker != worker_id: raise HTTPException(403,"Worker identity mismatch")
    result=workers.renew_lease(job_id,authenticated_worker)
    if not result: raise HTTPException(409,"Job lease cannot be renewed.")
    return result

@worker_router.post("/workers/{worker_id}/claim")
def claim_job(worker_id:str, authenticated_worker:str=Depends(require_worker_identity)):
    if authenticated_worker != worker_id: raise HTTPException(403,"Worker identity mismatch")
    return {"job":workers.claim(authenticated_worker)}
@worker_router.post("/jobs/{job_id}/finish")
def finish_job(job_id:str,payload:JobFinish,worker_id:str=Query(min_length=2,max_length=80),authenticated_worker:str=Depends(require_worker_identity)):
    if authenticated_worker != worker_id: raise HTTPException(403,"Worker identity mismatch")
    result=workers.finish(job_id,authenticated_worker,payload.result,payload.error)
    if not result: raise HTTPException(409,"Job is not running for this worker")
    return result

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
