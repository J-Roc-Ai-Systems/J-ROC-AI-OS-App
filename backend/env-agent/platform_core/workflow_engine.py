"""Durable workflow definitions and guarded execution state transitions."""
import uuid
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now
from .security import require_platform_access,audit
router=APIRouter(prefix="/platform/v1/workflows",tags=["J-ROC AI Workflow Engine"],dependencies=[Depends(require_platform_access)])
class Step(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 worker_capability:str=Field(min_length=2,max_length=80)
 input_template:dict=Field(default_factory=dict)
class Definition(BaseModel):
 workflow_id:str=Field(min_length=2,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
 name:str=Field(min_length=2,max_length=120)
 description:str=Field(default="",max_length=2000)
 steps:list[Step]=Field(min_length=1,max_length=50)
class Start(BaseModel): input:dict=Field(default_factory=dict)
class Transition(BaseModel):
 state:str=Field(pattern=r"^(running|completed|failed|skipped)$")
 output:dict=Field(default_factory=dict)
 error:str|None=Field(default=None,max_length=1000)
def read_definition(workflow_id):
 row=db.one("SELECT * FROM workflow_definitions WHERE workflow_id=?",(workflow_id,))
 if row:row["steps"]=db.decode(row["steps"],[])
 return row
def read_run(run_id):
 row=db.one("SELECT * FROM workflow_runs WHERE run_id=?",(run_id,))
 if not row:return None
 row["input"]=db.decode(row["input"],{});row["output"]=db.decode(row["output"])
 row["steps"]=db.many("SELECT * FROM workflow_run_steps WHERE run_id=? ORDER BY step_index",(run_id,))
 for step in row["steps"]:step["input"]=db.decode(step["input"],{});step["output"]=db.decode(step["output"])
 return row
@router.post("")
def create(payload:Definition):
 now=utc_now(); prior=read_definition(payload.workflow_id); version=(prior["version"]+1) if prior else 1
 db.execute("""INSERT INTO workflow_definitions(workflow_id,name,description,version,steps,enabled,created_at,updated_at)
 VALUES(?,?,?,?,?,1,?,?) ON CONFLICT(workflow_id) DO UPDATE SET name=excluded.name,description=excluded.description,
 version=excluded.version,steps=excluded.steps,enabled=1,updated_at=excluded.updated_at""",
 (payload.workflow_id,payload.name,payload.description,version,db.encode([s.model_dump() for s in payload.steps]),now,now))
 audit("workflow.define","workflow",payload.workflow_id,"version="+str(version));return read_definition(payload.workflow_id)
@router.get("")
def list_definitions():
 rows=db.many("SELECT * FROM workflow_definitions ORDER BY updated_at DESC")
 for row in rows:row["steps"]=db.decode(row["steps"],[])
 return rows
@router.post("/{workflow_id}/runs")
def start(workflow_id:str,payload:Start):
 definition=read_definition(workflow_id)
 if not definition or not definition["enabled"]:raise HTTPException(404,"Enabled workflow not found.")
 run_id=str(uuid.uuid4());now=utc_now()
 db.execute("INSERT INTO workflow_runs(run_id,workflow_id,state,input,started_at) VALUES(?,?,?,?,?)",(run_id,workflow_id,"queued",db.encode(payload.input),now))
 for i,step in enumerate(definition["steps"]):
  db.execute("INSERT INTO workflow_run_steps(step_id,run_id,step_index,step_name,state,input) VALUES(?,?,?,?,?,?)",
   (str(uuid.uuid4()),run_id,i,step["name"],"pending",db.encode(step.get("input_template",{}))))
 audit("workflow.start","workflow_run",run_id,workflow_id);return read_run(run_id)
@router.get("/runs")
def list_runs():return db.many("SELECT run_id,workflow_id,state,started_at,finished_at FROM workflow_runs ORDER BY started_at DESC LIMIT 200")
@router.get("/runs/{run_id}")
def get_run(run_id:str):
 result=read_run(run_id)
 if not result:raise HTTPException(404,"Workflow run not found.")
 return result
@router.patch("/runs/{run_id}/steps/{step_index}")
def transition(run_id:str,step_index:int,payload:Transition):
 run=db.one("SELECT * FROM workflow_runs WHERE run_id=?",(run_id,))
 step=db.one("SELECT * FROM workflow_run_steps WHERE run_id=? AND step_index=?",(run_id,step_index))
 if not run or not step:raise HTTPException(404,"Workflow run or step not found.")
 if run["state"] in {"completed","failed","cancelled"}:raise HTTPException(409,"Workflow run is terminal.")
 if payload.state=="running" and step["state"]!="pending":raise HTTPException(409,"Only pending steps can start.")
 if payload.state in {"completed","failed","skipped"} and step["state"]!="running":raise HTTPException(409,"Only running steps can finish.")
 now=utc_now()
 db.execute("UPDATE workflow_run_steps SET state=?,output=?,error=?,started_at=COALESCE(started_at,?),finished_at=? WHERE step_id=?",
  (payload.state,db.encode(payload.output),payload.error,now,now if payload.state in {"completed","failed","skipped"} else None,step["step_id"]))
 states=[r["state"] for r in db.many("SELECT state FROM workflow_run_steps WHERE run_id=?",(run_id,))]
 new_state="failed" if "failed" in states else "completed" if all(s in {"completed","skipped"} for s in states) else "running"
 db.execute("UPDATE workflow_runs SET state=?,finished_at=? WHERE run_id=?",(new_state,now if new_state in {"failed","completed"} else None,run_id))
 audit("workflow.step."+payload.state,"workflow_run",run_id,"step="+str(step_index));return read_run(run_id)
