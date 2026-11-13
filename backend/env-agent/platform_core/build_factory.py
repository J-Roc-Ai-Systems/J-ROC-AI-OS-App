"""Approval-gated build orchestration; execution belongs to isolated workers."""
import uuid
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now,JobSubmission
from .workers import workers
from .security import require_platform_access,audit
router=APIRouter(prefix="/platform/v1/builds",tags=["J-ROC AI Application Factory"],dependencies=[Depends(require_platform_access)])
class Recipe(BaseModel):
 recipe_id:str=Field(min_length=2,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
 name:str=Field(min_length=2,max_length=120)
 platform:str=Field(min_length=2,max_length=40)
 build_command:list[str]=Field(min_length=1,max_length=30)
 working_directory:str=Field(min_length=1,max_length=300)
 required_capability:str=Field(default="build.execute",min_length=2,max_length=80)
class RunRequest(BaseModel):
 project_id:str=Field(min_length=2,max_length=100)
 recipe_id:str=Field(min_length=2,max_length=80)
 source_revision:str=Field(min_length=7,max_length=80)
 parameters:dict=Field(default_factory=dict)
def read_recipe(recipe_id):
 return db.one("SELECT * FROM build_recipes WHERE recipe_id=?",(recipe_id,))
def read_run(run_id):
 row=db.one("SELECT * FROM build_runs WHERE run_id=?",(run_id,))
 if row:row["parameters"]=db.decode(row["parameters"],{});row["result"]=db.decode(row["result"])
 return row
@router.post("/recipes")
def create_recipe(p:Recipe):
 now=utc_now()
 db.execute("""INSERT INTO build_recipes(recipe_id,name,platform,build_command,working_directory,required_capability,enabled,created_at,updated_at)
 VALUES(?,?,?,?,?,?,1,?,?) ON CONFLICT(recipe_id) DO UPDATE SET name=excluded.name,platform=excluded.platform,
 build_command=excluded.build_command,working_directory=excluded.working_directory,required_capability=excluded.required_capability,updated_at=excluded.updated_at""",
 (p.recipe_id,p.name,p.platform,db.encode(p.build_command),p.working_directory,p.required_capability,now,now))
 audit("build.recipe.create","build_recipe",p.recipe_id)
 return db.one("SELECT * FROM build_recipes WHERE recipe_id=?",(p.recipe_id,))
@router.get("/recipes")
def recipes():
 rows=db.many("SELECT * FROM build_recipes ORDER BY name")
 for r in rows:r["build_command"]=db.decode(r["build_command"],[])
 return rows
@router.post("/runs")
def create_run(p:RunRequest):
 if not read_recipe(p.recipe_id):raise HTTPException(404,"Build recipe not found.")
 if not db.one("SELECT project_id FROM projects WHERE project_id=?",(p.project_id,)):raise HTTPException(404,"Project not found.")
 run_id=str(uuid.uuid4());now=utc_now()
 db.execute("""INSERT INTO build_runs(run_id,project_id,recipe_id,source_revision,parameters,state,created_at,updated_at)
 VALUES(?,?,?,?,?,'pending_approval',?,?)""",(run_id,p.project_id,p.recipe_id,p.source_revision,db.encode(p.parameters),now,now))
 audit("build.run.request","build_run",run_id,"approval_required")
 return read_run(run_id)
@router.post("/runs/{run_id}/approve")
def approve_run(run_id:str):
 run=read_run(run_id)
 if not run:raise HTTPException(404,"Build run not found.")
 if run["state"]!="pending_approval":raise HTTPException(409,"Build run is not awaiting approval.")
 recipe=read_recipe(run["recipe_id"])
 job=workers.submit(JobSubmission(job_type="build.execute",payload={"build_run_id":run_id,"project_id":run["project_id"],
  "recipe_id":run["recipe_id"],"source_revision":run["source_revision"],"parameters":run["parameters"],
  "required_capability":recipe["required_capability"]},
  priority=7,required_capability=recipe["required_capability"]))
 now=utc_now()
 db.execute("UPDATE build_runs SET state='queued',job_id=?,updated_at=? WHERE run_id=?",(job["job_id"],now,run_id))
 audit("build.run.approve","build_run",run_id,"job="+job["job_id"])
 return read_run(run_id)
@router.get("/runs")
def list_runs():
 return db.many("SELECT run_id,project_id,recipe_id,source_revision,state,job_id,created_at,updated_at FROM build_runs ORDER BY created_at DESC LIMIT 200")
@router.get("/runs/{run_id}")
def get_run(run_id:str):
 row=read_run(run_id)
 if not row:raise HTTPException(404,"Build run not found.")
 return row
