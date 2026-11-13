"""Wave Three, Four and Five shared service catalogue, workflow governance and policy gates."""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from .database import db
from .models import utc_now
from .security import audit

router = APIRouter(prefix="/platform/v1", tags=["J-ROC AI Waves Three to Five"])

WAVES = [
 {"wave":3,"name":"Governance and orchestration","batches":[
  (21,"Identity and access management","Role and permission foundations; production identity provider integration remains required."),
  (22,"Policy and approval engine","Default-deny controls for privileged operations and explicit approval records."),
  (23,"Workflow orchestration","Durable workflow definitions, state transitions and approval checkpoints."),
  (24,"Model routing and evaluation","Provider-neutral routing contracts; paid execution remains disabled by default."),
  (25,"Observability and telemetry","Operational event summaries, health counters and trace references."),
  (26,"Backup and recovery","Backup inventory, restore plans and recovery verification records."),
  (27,"Release governance","Release manifests, approval checkpoints and deployment records."),
  (28,"Platform administration","Service configuration registry and administrative audit trail."),
  (29,"Security operations","Security findings, severity tracking and remediation ownership."),
  (30,"Developer operations","Build, test and repository automation job contracts.")
 ]},
 {"wave":4,"name":"Universal repair and device operations","batches":[
  (31,"Repair intelligence","Repair case knowledge, symptoms, probable causes and verified remedies."),
  (32,"Device session management","Device registration, session lifecycle and explicit authorization boundaries."),
  (33,"Diagnostics engine","Structured diagnostic runs and evidence collection; no unauthorized device control."),
  (34,"Repair workflow engine","Repair intake, approved steps, technician notes and completion records."),
  (35,"Device compatibility","Model, operating-system, firmware and connection compatibility records."),
  (36,"Fleet management","Organization device inventories, assignment and fleet health summaries."),
  (37,"Update orchestration","Staged update plans and user approval; no silent firmware writes."),
  (38,"Service history and warranty","Repair history, parts references and warranty status records."),
  (39,"Repair reporting","Diagnostic reports, repair summaries and export metadata."),
  (40,"Repair quality and safety","Safety checklists, data-loss warnings and repair outcome review.")
 ]},
 {"wave":5,"name":"Academy and business operations","batches":[
  (41,"Academy learning platform","Courses, modules and lesson progress records."),
  (42,"AI tutoring and practice","Tutor session contracts and practice activity history."),
  (43,"Certification management","Assessment attempts, credential records and renewal tracking."),
  (44,"Customer relationship management","Customer profiles, organization contacts and interaction history."),
  (45,"Commerce foundations","Catalog, order and entitlement records; no payment capture enabled."),
  (46,"Marketing and campaigns","Campaign plans, audiences and approval-gated publication."),
  (47,"Content production","Content briefs, asset references and review workflows."),
  (48,"Business analytics","Operational metrics and report definitions with source lineage."),
  (49,"Customer support","Support cases, queues, escalation and resolution records."),
  (50,"Asset and resource management","Equipment, licenses and resource assignment inventory.")
 ]}
]

class WorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_type: str = Field(min_length=3,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
    title: str = Field(min_length=3,max_length=160)
    objective: str = Field(min_length=5,max_length=4000)
    batch: int | None = Field(default=None,ge=21,le=50)
    steps: list[str] = Field(default_factory=list,max_length=30)
    requires_approval: bool = True

class WorkflowDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(approve|reject)$")
    reason: str = Field(min_length=3,max_length=1000)

class PolicyCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=2,max_length=100)
    resource_type: str = Field(default="platform",max_length=80)
    resource_id: str = Field(default="",max_length=160)
    estimated_cost_usd: float = Field(default=0,ge=0,le=1000000)
    destructive: bool = False

def _ensure_schema():
    connection=db.connect()
    connection.execute("""CREATE TABLE IF NOT EXISTS platform_workflows(
      workflow_id TEXT PRIMARY KEY,workflow_type TEXT NOT NULL,title TEXT NOT NULL,objective TEXT NOT NULL,
      batch INTEGER,steps TEXT NOT NULL,state TEXT NOT NULL,requires_approval INTEGER NOT NULL,
      decision_reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
    connection.execute("""CREATE TABLE IF NOT EXISTS platform_policy_decisions(
      decision_id TEXT PRIMARY KEY,action TEXT NOT NULL,resource_type TEXT NOT NULL,resource_id TEXT NOT NULL,
      outcome TEXT NOT NULL,reason TEXT NOT NULL,estimated_cost_usd REAL NOT NULL,created_at TEXT NOT NULL)""")

def _workflow(row: dict[str,Any] | None):
    if not row: return None
    row["steps"]=db.decode(row["steps"],[])
    row["requires_approval"]=bool(row["requires_approval"])
    return row

@router.get("/waves")
def list_waves():
    return {"waves":WAVES,"batch_count":30,"first_batch":21,"last_batch":50,
      "implementation_note":"Catalogue and shared workflow governance are implemented here; individual batch adapters are tracked separately."}

@router.post("/workflows")
def create_workflow(item:WorkflowCreate):
    _ensure_schema()
    if item.batch is not None and not any(item.batch==b[0] for w in WAVES for b in w["batches"]):
        raise HTTPException(400,"Batch is not part of Waves Three through Five.")
    workflow_id=str(uuid.uuid4()); now=utc_now()
    state="awaiting_approval" if item.requires_approval else "queued"
    db.execute("""INSERT INTO platform_workflows(workflow_id,workflow_type,title,objective,batch,steps,state,requires_approval,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?)""",(workflow_id,item.workflow_type,item.title,item.objective,item.batch,db.encode(item.steps),state,int(item.requires_approval),now,now))
    audit("workflow.create","workflow",workflow_id,item.workflow_type)
    return _workflow(db.one("SELECT * FROM platform_workflows WHERE workflow_id=?",(workflow_id,)))

@router.get("/workflows")
def list_workflows(state:str|None=None,limit:int=Query(default=100,ge=1,le=500)):
    _ensure_schema()
    if state:
        rows=db.many("SELECT * FROM platform_workflows WHERE state=? ORDER BY created_at DESC LIMIT ?",(state,limit))
    else:
        rows=db.many("SELECT * FROM platform_workflows ORDER BY created_at DESC LIMIT ?",(limit,))
    return [_workflow(row) for row in rows]

@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id:str):
    _ensure_schema()
    row=_workflow(db.one("SELECT * FROM platform_workflows WHERE workflow_id=?",(workflow_id,)))
    if not row: raise HTTPException(404,"Workflow not found.")
    return row

@router.post("/workflows/{workflow_id}/decision")
def decide_workflow(workflow_id:str,item:WorkflowDecision):
    _ensure_schema()
    row=db.one("SELECT * FROM platform_workflows WHERE workflow_id=?",(workflow_id,))
    if not row: raise HTTPException(404,"Workflow not found.")
    if row["state"]!="awaiting_approval": raise HTTPException(409,"Workflow is not awaiting approval.")
    state="approved_queued" if item.decision=="approve" else "rejected"
    db.execute("UPDATE platform_workflows SET state=?,decision_reason=?,updated_at=? WHERE workflow_id=?",
      (state,item.reason,utc_now(),workflow_id))
    audit("workflow."+item.decision,"workflow",workflow_id,item.reason)
    return get_workflow(workflow_id)

@router.post("/workflows/{workflow_id}/cancel")
def cancel_workflow(workflow_id:str):
    _ensure_schema()
    row=db.one("SELECT state FROM platform_workflows WHERE workflow_id=?",(workflow_id,))
    if not row: raise HTTPException(404,"Workflow not found.")
    if row["state"] in {"completed","cancelled","rejected"}: raise HTTPException(409,"Workflow is already terminal.")
    db.execute("UPDATE platform_workflows SET state='cancelled',updated_at=? WHERE workflow_id=?",(utc_now(),workflow_id))
    audit("workflow.cancel","workflow",workflow_id)
    return get_workflow(workflow_id)

@router.post("/policy/evaluate")
def evaluate_policy(item:PolicyCheck):
    _ensure_schema()
    action=item.action.lower()
    outcome="allow"; reason="Read-only or non-privileged platform operation."
    if item.estimated_cost_usd>0:
        allow=os.getenv("JROCAI_ALLOW_PAID_CLOUD","false").lower()=="true"
        try: limit=float(os.getenv("JROCAI_MONTHLY_SPENDING_LIMIT_USD","0"))
        except ValueError: limit=0
        if not allow or limit<=0:
            outcome="deny"; reason="Zero-dollar spending gate blocks paid execution."
        elif item.estimated_cost_usd>limit:
            outcome="deny"; reason="Estimated cost exceeds the configured monthly spending limit."
        else:
            outcome="requires_approval"; reason="Paid execution requires a separate explicit approval."
    elif any(term in action for term in ("bypass_security","credential_dump","steal_token","disable_protection")):
        outcome="deny"; reason="Operation violates the platform security policy."
    elif item.destructive or any(term in action for term in ("erase","wipe","flash_firmware","unlock_bootloader","publish","release","install_package","delete")):
        outcome="requires_approval"; reason="Destructive or externally visible operation requires explicit approval."
    decision_id=str(uuid.uuid4())
    db.execute("""INSERT INTO platform_policy_decisions(decision_id,action,resource_type,resource_id,outcome,reason,estimated_cost_usd,created_at)
      VALUES(?,?,?,?,?,?,?,?)""",(decision_id,item.action,item.resource_type,item.resource_id,outcome,reason,item.estimated_cost_usd,utc_now()))
    audit("policy."+outcome,item.resource_type,item.resource_id or decision_id,item.action+": "+reason)
    return {"decision_id":decision_id,"outcome":outcome,"reason":reason,"execution_performed":False}

@router.get("/policy/decisions")
def list_policy_decisions(limit:int=Query(default=100,ge=1,le=500)):
    _ensure_schema()
    return db.many("SELECT * FROM platform_policy_decisions ORDER BY created_at DESC LIMIT ?",(limit,))

@router.get("/governance/overview")
def governance_overview():
    _ensure_schema()
    states=db.many("SELECT state,COUNT(*) AS count FROM platform_workflows GROUP BY state")
    decisions=db.many("SELECT outcome,COUNT(*) AS count FROM platform_policy_decisions GROUP BY outcome")
    return {"workflow_states":{r["state"]:r["count"] for r in states},
      "policy_decisions":{r["outcome"]:r["count"] for r in decisions},
      "execution_policy":"approval-gated; this API does not execute workflow payloads",
      "identity_boundary":"single gateway token; per-user roles and tenant isolation are not yet implemented"}
