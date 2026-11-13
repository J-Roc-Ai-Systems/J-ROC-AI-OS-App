"""Durable Wave Six through Ten service registry and approval-gated agent job queue."""
import json, os, uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from .database import db
from .models import utc_now
from .security import audit, require_platform_access

router=APIRouter(prefix="/platform/v1",tags=["J-ROC AI Waves Six to Ten"],dependencies=[Depends(require_platform_access)])
WAVES=[
 {"wave":6,"name":"Agent workforce and source intelligence","batches":[(51,"Platform-wide agent registry"),(52,"Source intelligence agent"),(53,"Repository intelligence"),(54,"Code generation governance"),(55,"Build orchestration"),(56,"Test orchestration"),(57,"Documentation intelligence"),(58,"Agent collaboration"),(59,"Agent memory and knowledge"),(60,"Agent performance and evaluation")]},
 {"wave":7,"name":"Developer platform and application factory","batches":[(61,"Software development kits"),(62,"Application factory"),(63,"Website factory"),(64,"Workflow designer"),(65,"Interface component registry"),(66,"Application integration gateway"),(67,"API lifecycle management"),(68,"Developer workspaces"),(69,"Package and dependency governance"),(70,"Release and deployment automation")]},
 {"wave":8,"name":"Operating system and device intelligence","batches":[(71,"Cross-device operating system services"),(72,"Device identity and enrollment"),(73,"Local-first model runtime"),(74,"Model router and fallback"),(75,"Voice and accessibility services"),(76,"File and knowledge intelligence"),(77,"System health and diagnostics"),(78,"Connectivity and network management"),(79,"Backup synchronization"),(80,"Privacy and permission center")]},
 {"wave":9,"name":"Enterprise operations and cybersecurity","batches":[(81,"Organization and tenant administration"),(82,"Role and permission administration"),(83,"Single sign-on and multi-factor readiness"),(84,"Security monitoring"),(85,"Threat intelligence"),(86,"Vulnerability management"),(87,"Audit and compliance"),(88,"Data governance"),(89,"Enterprise service management"),(90,"Business continuity")]},
 {"wave":10,"name":"Marketplace, revenue and ecosystem expansion","batches":[(91,"Platform marketplace"),(92,"Extension developer program"),(93,"Subscription and entitlement management"),(94,"Billing ledger foundations"),(95,"Partner and reseller operations"),(96,"Customer onboarding"),(97,"Growth and attribution analytics"),(98,"Customer success intelligence"),(99,"Platform export and portability"),(100,"Ecosystem governance and certification")]}
]
BATCHES={b[0]:{"batch":b[0],"name":b[1],"wave":w["wave"],"wave_name":w["name"]} for w in WAVES for b in w["batches"]}
BLOCKED=("arbitrary_code","firmware_write","device_unlock","security_bypass","payment_capture","secret_export","shell_command")

class AgentRegistration(BaseModel):
 model_config=ConfigDict(extra="forbid")
 agent_id:str=Field(min_length=2,max_length=100,pattern=r"^[a-zA-Z0-9._-]+$")
 display_name:str=Field(min_length=2,max_length=160)
 capabilities:list[str]=Field(default_factory=list,max_length=50)

class AgentJobCreate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 job_type:str=Field(min_length=3,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
 title:str=Field(min_length=3,max_length=180)
 objective:str=Field(min_length=5,max_length=4000)
 batch:int=Field(ge=51,le=100)
 agent_id:str=Field(min_length=2,max_length=100)
 repository:str|None=Field(default=None,max_length=240)
 file_scope:list[str]=Field(default_factory=list,max_length=100)
 approval_required:bool=True

class JobDecision(BaseModel):
 model_config=ConfigDict(extra="forbid")
 decision:str=Field(pattern="^(approve|reject)$")
 reason:str=Field(min_length=3,max_length=1000)

def _ensure():
 c=db.connect()
 c.execute("""CREATE TABLE IF NOT EXISTS platform_agent_registry(agent_id TEXT PRIMARY KEY,display_name TEXT NOT NULL,capabilities TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
 c.execute("""CREATE TABLE IF NOT EXISTS platform_agent_jobs(job_id TEXT PRIMARY KEY,job_type TEXT NOT NULL,title TEXT NOT NULL,objective TEXT NOT NULL,batch INTEGER NOT NULL,agent_id TEXT NOT NULL,repository TEXT,file_scope TEXT NOT NULL,state TEXT NOT NULL,approval_required INTEGER NOT NULL,decision_reason TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
 c.execute("CREATE INDEX IF NOT EXISTS idx_agent_jobs_state ON platform_agent_jobs(state,created_at)")
 columns={row["name"] for row in c.execute("PRAGMA table_info(platform_agent_jobs)").fetchall()}
 if "worker_job_id" not in columns:c.execute("ALTER TABLE platform_agent_jobs ADD COLUMN worker_job_id TEXT")

def _job(row:dict[str,Any]|None):
 if not row:return None
 row["file_scope"]=db.decode(row["file_scope"],[])
 row["approval_required"]=bool(row["approval_required"])
 return row

@router.get("/waves/6-10")
def list_waves_six_to_ten():
 return {"waves":[{"wave":w["wave"],"name":w["name"],"batches":[{"batch":b,"name":n} for b,n in w["batches"]]} for w in WAVES],"batch_count":50,"first_batch":51,"last_batch":100,"execution_boundary":"Job requests are queued only; trusted runners and approval are required.","spending_policy":"Zero-dollar by default."}

@router.post("/agents")
def register_agent(item:AgentRegistration):
 _ensure()
 if db.one("SELECT agent_id FROM platform_agent_registry WHERE agent_id=?",(item.agent_id,)):raise HTTPException(409,"Agent already registered.")
 now=utc_now()
 db.execute("INSERT INTO platform_agent_registry VALUES(?,?,?,?,?,?)",(item.agent_id,item.display_name,db.encode(item.capabilities),"registered",now,now))
 audit("agent.register","agent",item.agent_id,item.display_name)
 return {"agent_id":item.agent_id,"display_name":item.display_name,"capabilities":item.capabilities,"status":"registered"}

@router.get("/agents")
def list_agents():
 _ensure(); rows=db.many("SELECT * FROM platform_agent_registry ORDER BY agent_id")
 for r in rows:r["capabilities"]=db.decode(r["capabilities"],[])
 return {"agents":rows,"count":len(rows)}

@router.post("/agent-jobs")
def create_agent_job(item:AgentJobCreate):
 _ensure()
 if item.batch not in BATCHES:raise HTTPException(400,"Unknown batch.")
 if any(term in (item.job_type+" "+item.objective).lower() for term in BLOCKED):raise HTTPException(403,"Operation is outside the approved agent boundary.")
 if not db.one("SELECT agent_id FROM platform_agent_registry WHERE agent_id=? AND status='registered'",(item.agent_id,)):raise HTTPException(404,"Registered agent required.")
 if item.repository and (len(item.repository.split("/"))!=2 or ".." in item.repository):raise HTTPException(422,"Repository must use owner/repository format.")
 scope=[]
 for path in item.file_scope:
  p=path.replace(chr(92),"/")
  if p.startswith("/") or ".." in p.split("/") or len(p)>240:raise HTTPException(422,"Unsafe file scope.")
  scope.append(p)
 jid=str(uuid.uuid4()); now=utc_now(); state="awaiting_approval" if item.approval_required else "queued"
 db.execute("INSERT INTO platform_agent_jobs(job_id,job_type,title,objective,batch,agent_id,repository,file_scope,state,approval_required,decision_reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(jid,item.job_type,item.title,item.objective,item.batch,item.agent_id,item.repository,db.encode(scope),state,int(item.approval_required),None,now,now))
 audit("agent_job.create","agent_job",jid,item.agent_id)
 return _job(db.one("SELECT * FROM platform_agent_jobs WHERE job_id=?",(jid,)))

@router.get("/agent-jobs")
def list_agent_jobs(state:str|None=None,limit:int=Query(default=100,ge=1,le=500)):
 _ensure()
 rows=db.many("SELECT * FROM platform_agent_jobs WHERE state=? ORDER BY created_at DESC LIMIT ?",(state,limit)) if state else db.many("SELECT * FROM platform_agent_jobs ORDER BY created_at DESC LIMIT ?",(limit,))
 return [_job(r) for r in rows]

@router.post("/agent-jobs/{job_id}/decision")
def decide_agent_job(job_id:str,item:JobDecision):
 _ensure(); row=db.one("SELECT state FROM platform_agent_jobs WHERE job_id=?",(job_id,))
 if not row:raise HTTPException(404,"Agent job not found.")
 if row["state"]!="awaiting_approval":raise HTTPException(409,"Job is not awaiting approval.")
 state="approved_queued" if item.decision=="approve" else "rejected"
 db.execute("UPDATE platform_agent_jobs SET state=?,decision_reason=?,updated_at=? WHERE job_id=?",(state,item.reason,utc_now(),job_id))
 audit("agent_job."+item.decision,"agent_job",job_id,item.reason)
 return _job(db.one("SELECT * FROM platform_agent_jobs WHERE job_id=?",(job_id,)))

@router.get("/environment/readiness")
def environment_readiness():
 names=("JROCAI_GATEWAY_TOKEN","JROCAI_PLATFORM_DATABASE","JROCAI_FILE_ROOT","JROCAI_ALLOW_PAID_CLOUD","JROCAI_MONTHLY_SPENDING_LIMIT_USD")
 try:limit=float(os.getenv("JROCAI_MONTHLY_SPENDING_LIMIT_USD","0"))
 except ValueError:limit=0
 enabled=os.getenv("JROCAI_ALLOW_PAID_CLOUD","false").lower()=="true" and limit>0
 return {"secret_values_returned":False,"variables":[{"name":n,"configured":bool(os.getenv(n))} for n in names],"paid_execution_enabled":enabled,"spending_limit_usd":limit if enabled else 0}


# Specialized Wave 6–10 service contracts. These remain metadata/workflow services;
# execution is delegated to the authenticated, leased production worker queue.
from .models import JobSubmission
from .workers import workers

RESOURCE_TYPES = {
 "agent_profiles":51,"source_reviews":52,"repository_snapshots":53,"change_proposals":54,
 "build_requests":55,"test_runs":56,"documentation_reviews":57,"agent_delegations":58,
 "agent_knowledge":59,"agent_evaluations":60,"sdk_releases":61,"application_projects":62,
 "website_projects":63,"workflow_definitions":64,"interface_components":65,"integrations":66,
 "api_versions":67,"developer_workspaces":68,"dependency_reviews":69,"release_plans":70,
 "operating_system_services":71,"device_enrollments":72,"local_models":73,"model_routes":74,
 "accessibility_profiles":75,"file_indexes":76,"system_diagnostics":77,"network_profiles":78,
 "backup_manifests":79,"privacy_consents":80,"organizations":81,"role_assignments":82,
 "identity_providers":83,"security_findings":84,"threat_indicators":85,"vulnerability_findings":86,
 "compliance_controls":87,"data_policies":88,"service_incidents":89,"recovery_plans":90,
 "marketplace_extensions":91,"extension_reviews":92,"entitlements":93,"billing_entries":94,
 "partners":95,"onboarding_records":96,"attribution_events":97,"customer_health":98,
 "export_requests":99,"certification_reviews":100
}
RESOURCE_STATES={"draft","pending","awaiting_approval","approved","active","paused","completed","rejected","archived"}
RESOURCE_TERMINAL={"completed","rejected","archived"}
SENSITIVE_KEYS=("password","secret","token","credential","private_key","api_key","authorization","access_key")
RESOURCE_REQUIRED={
 "source_reviews":("repository",),"repository_snapshots":("repository","commit"),
 "change_proposals":("repository","changes"),"build_requests":("project_id","build_target"),
 "test_runs":("suite",),"workflow_definitions":("steps",),"device_enrollments":("device_id","owner_confirmation"),
 "local_models":("model_id","runtime"),"model_routes":("route_name","fallback_policy"),
 "security_findings":("title","severity","source"),"threat_indicators":("indicator","source"),
 "vulnerability_findings":("asset","finding_id","severity"),"marketplace_extensions":("extension_id","version","manifest"),
 "extension_reviews":("extension_id","reviewer"),"entitlements":("subject_id","entitlement"),
 "export_requests":("subject_id","format","scope"),"privacy_consents":("subject_id","purpose","granted")
}
def _clean_resource(value):
 if isinstance(value,dict):
  return {str(k):_clean_resource(v) for k,v in value.items() if not any(x in str(k).lower() for x in SENSITIVE_KEYS)}
 if isinstance(value,list):return [_clean_resource(v) for v in value[:500]]
 if isinstance(value,str):return value[:20000]
 if value is None or isinstance(value,(bool,int,float)):return value
 return str(value)[:2000]

def _resource_schema():
 c=db.connect()
 c.execute("""CREATE TABLE IF NOT EXISTS wave610_resources(
  resource_id TEXT PRIMARY KEY,resource_type TEXT NOT NULL,batch INTEGER NOT NULL,
  title TEXT NOT NULL,state TEXT NOT NULL,owner_reference TEXT,data TEXT NOT NULL,
  created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
 c.execute("CREATE INDEX IF NOT EXISTS idx_wave610_resources ON wave610_resources(resource_type,state,updated_at)")

class ResourceCreate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 title:str=Field(min_length=2,max_length=180)
 state:str=Field(default="draft",pattern="^(draft|pending|awaiting_approval|approved|active|paused|completed|rejected|archived)$")
 owner_reference:str|None=Field(default=None,max_length=180)
 data:dict[str,Any]=Field(default_factory=dict)

class ResourceState(BaseModel):
 model_config=ConfigDict(extra="forbid")
 state:str=Field(pattern="^(draft|pending|awaiting_approval|approved|active|paused|completed|rejected|archived)$")
 reason:str=Field(min_length=3,max_length=1000)

@router.get("/wave-resources/catalog")
def wave_resource_catalog():
 return {"resources":[{"resource_type":k,"batch":v,"wave":(v-1)//10+1,"required_fields":list(RESOURCE_REQUIRED.get(k,()))} for k,v in RESOURCE_TYPES.items()],"count":len(RESOURCE_TYPES)}

@router.post("/wave-resources/{resource_type}")
def create_wave_resource(resource_type:str,item:ResourceCreate):
 if resource_type not in RESOURCE_TYPES:raise HTTPException(404,"Wave resource type is not registered.")
 required=RESOURCE_REQUIRED.get(resource_type,())
 missing=[key for key in required if key not in item.data or item.data[key] in (None,"",[],{})]
 if missing:raise HTTPException(422,{"message":"Required domain fields are missing.","fields":missing})
 data=_clean_resource(item.data)
 if len(json.dumps(data,ensure_ascii=False))>100000:raise HTTPException(413,"Resource data exceeds 100 kilobytes.")
 if resource_type=="device_enrollments" and data.get("owner_confirmation") is not True:raise HTTPException(403,"Device owner confirmation is required.")
 if resource_type=="local_models" and data.get("runtime") not in {"local","localhost"}:raise HTTPException(403,"This model registry accepts local runtimes only under the zero-dollar default.")
 if resource_type=="marketplace_extensions" and item.state in {"active","approved"}:raise HTTPException(409,"Extensions must pass a separate review before activation.")
 if resource_type=="entitlements" and any(k in data for k in ("card_number","payment_token","payment_method")):raise HTTPException(422,"Payment credentials are not accepted by entitlement records.")
 _resource_schema(); rid=str(uuid.uuid4()); now=utc_now()
 db.execute("INSERT INTO wave610_resources VALUES(?,?,?,?,?,?,?,?,?)",(rid,resource_type,RESOURCE_TYPES[resource_type],item.title,item.state,item.owner_reference,db.encode(data),now,now))
 audit("wave610_resource.create",resource_type,rid,item.title)
 return _wave_resource(db.one("SELECT * FROM wave610_resources WHERE resource_id=?",(rid,)))

def _wave_resource(row):
 if row:row["data"]=db.decode(row["data"],{})
 return row

@router.get("/wave-resources/{resource_type}")
def list_wave_resources(resource_type:str,state:str|None=None,limit:int=Query(default=100,ge=1,le=500)):
 if resource_type not in RESOURCE_TYPES:raise HTTPException(404,"Wave resource type is not registered.")
 _resource_schema()
 rows=db.many("SELECT * FROM wave610_resources WHERE resource_type=? AND state=? ORDER BY updated_at DESC LIMIT ?",(resource_type,state,limit)) if state else db.many("SELECT * FROM wave610_resources WHERE resource_type=? ORDER BY updated_at DESC LIMIT ?",(resource_type,limit))
 return [_wave_resource(r) for r in rows]

@router.get("/wave-resources/{resource_type}/{resource_id}")
def get_wave_resource(resource_type:str,resource_id:str):
 if resource_type not in RESOURCE_TYPES:raise HTTPException(404,"Wave resource type is not registered.")
 _resource_schema(); row=_wave_resource(db.one("SELECT * FROM wave610_resources WHERE resource_type=? AND resource_id=?",(resource_type,resource_id)))
 if not row:raise HTTPException(404,"Wave resource not found.")
 return row

@router.patch("/wave-resources/{resource_type}/{resource_id}/state")
def update_wave_resource_state(resource_type:str,resource_id:str,item:ResourceState):
 if resource_type not in RESOURCE_TYPES:raise HTTPException(404,"Wave resource type is not registered.")
 _resource_schema(); row=db.one("SELECT state FROM wave610_resources WHERE resource_type=? AND resource_id=?",(resource_type,resource_id))
 if not row:raise HTTPException(404,"Wave resource not found.")
 if row["state"] in RESOURCE_TERMINAL:raise HTTPException(409,"Terminal resource cannot be reopened.")
 if item.state=="active" and resource_type in {"marketplace_extensions","extension_reviews","release_plans","identity_providers"} and row["state"] not in {"approved"}:raise HTTPException(409,"This resource requires approval before activation.")
 db.execute("UPDATE wave610_resources SET state=?,updated_at=? WHERE resource_type=? AND resource_id=?",(item.state,utc_now(),resource_type,resource_id))
 audit("wave610_resource.state",resource_type,resource_id,item.reason)
 return get_wave_resource(resource_type,resource_id)

@router.post("/agent-jobs/{job_id}/dispatch")
def dispatch_approved_agent_job(job_id:str):
 _ensure()
 row=db.one("SELECT * FROM platform_agent_jobs WHERE job_id=?",(job_id,))
 if not row:raise HTTPException(404,"Agent job not found.")
 if row["state"]!="approved_queued":raise HTTPException(409,"Agent job must be explicitly approved before dispatch.")
 if row.get("worker_job_id"):raise HTTPException(409,"Agent job was already dispatched.")
 payload={"agent_job_id":job_id,"agent_id":row["agent_id"],"batch":row["batch"],"job_type":row["job_type"],"title":row["title"],"objective":row["objective"],"repository":row["repository"],"file_scope":db.decode(row["file_scope"],[]),"execution_contract":"structured_task_only_no_arbitrary_shell"}
 queued=workers.submit(JobSubmission(job_type="agent.structured_task",payload=payload,priority=5,required_capability="agent:"+row["agent_id"],max_attempts=2))
 db.execute("UPDATE platform_agent_jobs SET worker_job_id=?,updated_at=? WHERE job_id=?",(queued["job_id"],utc_now(),job_id))
 audit("agent_job.dispatch","agent_job",job_id,queued["job_id"])
 return {"agent_job_id":job_id,"worker_job_id":queued["job_id"],"worker_queue_state":queued["state"],"required_worker_capability":"agent:"+row["agent_id"]}


DEFAULT_AGENTS=[
 ("source-agent","Source Agent",["repository.inspect","source.search","change.propose"]),
 ("android-agent","Android Agent",["android.inspect","android.build","android.test"]),
 ("environment-agent","Environment Agent",["environment.readiness","secret.references"]),
 ("test-agent","Test Agent",["tests.plan","tests.run","results.report"]),
 ("security-agent","Security Agent",["security.review","dependency.audit"]),
 ("documentation-agent","Documentation Agent",["documentation.review","documentation.propose"]),
 ("build-agent","Build Agent",["build.execute","artifact.verify"]),
 ("release-agent","Release Agent",["release.validate","release.package"]),
 ("repair-agent","Repair Intelligence Agent",["repair.diagnostics","device.compatibility"]),
 ("academy-agent","Academy Agent",["academy.course","academy.progress"]),
 ("website-agent","Website Factory Agent",["website.generate","brand.validate"]),
 ("model-agent","Model Routing Agent",["model.local.discover","model.evaluate"]),
 ("enterprise-agent","Enterprise Operations Agent",["enterprise.audit","compliance.review"]),
 ("marketplace-agent","Marketplace Agent",["extension.validate","marketplace.catalog"])
]
def ensure_default_agents():
 _ensure()
 created=[]
 for agent_id,name,capabilities in DEFAULT_AGENTS:
  if not db.one("SELECT agent_id FROM platform_agent_registry WHERE agent_id=?",(agent_id,)):
   now=utc_now()
   db.execute("INSERT INTO platform_agent_registry(agent_id,display_name,capabilities,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",(agent_id,name,db.encode(capabilities),"registered",now,now))
   audit("agent.bootstrap","agent",agent_id,"platform default agent registered")
   created.append(agent_id)
 return {"registered":len(DEFAULT_AGENTS),"created":created}
