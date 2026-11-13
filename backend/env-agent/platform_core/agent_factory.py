"""Versioned, permission-bounded agent definitions. No generated code is executed here."""
import uuid
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now
from .security import require_platform_access,audit
router=APIRouter(prefix="/platform/v1/agents",tags=["J-ROC AI Agent Factory"],dependencies=[Depends(require_platform_access)])
ALLOWED_PERMISSIONS={"platform.read","jobs.submit","devices.read","knowledge.read","files.read","build.request","repair.guidance","notifications.read"}
class AgentDefinition(BaseModel):
 agent_id:str=Field(min_length=2,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
 name:str=Field(min_length=2,max_length=120)
 purpose:str=Field(min_length=5,max_length=1000)
 capabilities:list[str]=Field(min_length=1,max_length=40)
 permissions:list[str]=Field(default_factory=list,max_length=20)
 worker_capability:str=Field(min_length=2,max_length=80)
 configuration:dict=Field(default_factory=dict)
def read_agent(agent_id):
 row=db.one("SELECT * FROM agent_definitions WHERE agent_id=?",(agent_id,))
 if not row:return None
 version=db.one("SELECT * FROM agent_versions WHERE agent_id=? AND version=?",(agent_id,row["current_version"])) if row["current_version"] else None
 if version:
  for key in ("capabilities","permissions","configuration","execution_policy"):version[key]=db.decode(version[key],{})
 row["current"]=version
 return row
@router.post("")
def define_agent(p:AgentDefinition):
 invalid=set(p.permissions)-ALLOWED_PERMISSIONS
 if invalid:raise HTTPException(422,"Agent requested permissions outside the approved capability allowlist.")
 now=utc_now();prior=db.one("SELECT current_version FROM agent_definitions WHERE agent_id=?",(p.agent_id,))
 version=(prior["current_version"] if prior else 0)+1
 if not prior:
  db.execute("INSERT INTO agent_definitions(agent_id,name,purpose,state,current_version,created_at,updated_at) VALUES(?,?,?,'draft',0,?,?)",
   (p.agent_id,p.name,p.purpose,now,now))
 else:
  db.execute("UPDATE agent_definitions SET name=?,purpose=?,state='draft',updated_at=? WHERE agent_id=?",(p.name,p.purpose,now,p.agent_id))
 version_id=str(uuid.uuid4())
 policy={"sandbox_required":True,"network_access":"deny_by_default","secret_access":"environment_agent_references_only","generated_code_execution":False}
 db.execute("""INSERT INTO agent_versions(agent_version_id,agent_id,version,capabilities,permissions,worker_capability,configuration,execution_policy,state,created_at)
 VALUES(?,?,?,?,?,?,?,?,?,?)""",(version_id,p.agent_id,version,db.encode(p.capabilities),db.encode(p.permissions),p.worker_capability,db.encode(p.configuration),db.encode(policy),"draft",now))
 audit("agent.define","agent",p.agent_id,"version="+str(version))
 return {"agent":read_agent(p.agent_id),"draft_version":version}
@router.get("")
def list_agents():
 rows=db.many("SELECT agent_id FROM agent_definitions ORDER BY updated_at DESC")
 return [read_agent(row["agent_id"]) for row in rows]
@router.get("/{agent_id}")
def get_agent(agent_id:str):
 row=read_agent(agent_id)
 if not row:raise HTTPException(404,"Agent not found.")
 return row
@router.post("/{agent_id}/publish")
def publish_agent(agent_id:str):
 agent=db.one("SELECT * FROM agent_definitions WHERE agent_id=?",(agent_id,))
 if not agent:raise HTTPException(404,"Agent not found.")
 draft=db.one("SELECT * FROM agent_versions WHERE agent_id=? AND state='draft' ORDER BY version DESC LIMIT 1",(agent_id,))
 if not draft:raise HTTPException(409,"No draft agent version is available.")
 db.execute("UPDATE agent_versions SET state='superseded' WHERE agent_id=? AND state='published'",(agent_id,))
 db.execute("UPDATE agent_versions SET state='published' WHERE agent_version_id=?",(draft["agent_version_id"],))
 db.execute("UPDATE agent_definitions SET state='active',current_version=?,updated_at=? WHERE agent_id=?",(draft["version"],utc_now(),agent_id))
 audit("agent.publish","agent",agent_id,"version="+str(draft["version"]))
 return read_agent(agent_id)
@router.post("/{agent_id}/disable")
def disable_agent(agent_id:str):
 if not db.one("SELECT agent_id FROM agent_definitions WHERE agent_id=?",(agent_id,)):raise HTTPException(404,"Agent not found.")
 db.execute("UPDATE agent_definitions SET state='disabled',updated_at=? WHERE agent_id=?",(utc_now(),agent_id))
 audit("agent.disable","agent",agent_id)
 return read_agent(agent_id)
