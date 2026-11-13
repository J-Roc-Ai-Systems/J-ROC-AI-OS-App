"""Repair compatibility profiles and non-invasive diagnostic session tracking."""
import uuid
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now
from .security import require_platform_access,audit
router=APIRouter(prefix="/platform/v1/repair",tags=["J-Bot Repair Intelligence"],dependencies=[Depends(require_platform_access)])
class Profile(BaseModel):
 profile_id:str=Field(min_length=2,max_length=100,pattern=r"^[a-zA-Z0-9._-]+$")
 manufacturer:str=Field(min_length=1,max_length=100)
 model:str=Field(min_length=1,max_length=120)
 operating_system:str=Field(min_length=1,max_length=80)
 supported_methods:list[str]=Field(default_factory=lambda:["usb","wireless"],max_length=5)
 safety_notes:list[str]=Field(default_factory=list,max_length=40)
 source_reference:str=Field(min_length=1,max_length=500)
class DiagnosticStart(BaseModel):
 device_id:str|None=Field(default=None,max_length=120)
 profile_id:str|None=Field(default=None,max_length=100)
 issue_summary:str=Field(min_length=5,max_length=2000)
 connection_method:str=Field(pattern=r"^(usb|wireless|local-only)$")
class DiagnosticUpdate(BaseModel):
 state:str=Field(pattern=r"^(investigating|awaiting_user|resolved|closed)$")
 findings:list[str]=Field(default_factory=list,max_length=100)
 next_actions:list[str]=Field(default_factory=list,max_length=50)
def read_profile(profile_id):
 row=db.one("SELECT * FROM repair_profiles WHERE profile_id=?",(profile_id,))
 if row:row["supported_methods"]=db.decode(row["supported_methods"],[]);row["safety_notes"]=db.decode(row["safety_notes"],[])
 return row
def read_session(session_id):
 row=db.one("SELECT * FROM diagnostic_sessions WHERE session_id=?",(session_id,))
 if row:row["findings"]=db.decode(row["findings"],[]);row["next_actions"]=db.decode(row["next_actions"],[])
 return row
@router.post("/profiles")
def add_profile(p:Profile):
 if not p.supported_methods or any(method not in {"usb","wireless","local-only"} for method in p.supported_methods):
  raise HTTPException(422,"Repair profiles may use only USB, wireless or local-only diagnostic methods.")
 now=utc_now()
 db.execute("""INSERT INTO repair_profiles(profile_id,manufacturer,model,operating_system,supported_methods,safety_notes,source_reference,created_at,updated_at)
 VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET manufacturer=excluded.manufacturer,model=excluded.model,
 operating_system=excluded.operating_system,supported_methods=excluded.supported_methods,safety_notes=excluded.safety_notes,
 source_reference=excluded.source_reference,updated_at=excluded.updated_at""",
 (p.profile_id,p.manufacturer,p.model,p.operating_system,db.encode(p.supported_methods),db.encode(p.safety_notes),p.source_reference,now,now))
 audit("repair.profile.register","repair_profile",p.profile_id);return read_profile(p.profile_id)
@router.get("/profiles")
def profiles():
 rows=db.many("SELECT profile_id FROM repair_profiles ORDER BY manufacturer,model")
 return [read_profile(r["profile_id"]) for r in rows]
@router.post("/sessions")
def start(p:DiagnosticStart):
 if p.device_id and not db.one("SELECT device_id FROM devices WHERE device_id=?",(p.device_id,)):raise HTTPException(404,"Device is not registered.")
 if p.profile_id and not read_profile(p.profile_id):raise HTTPException(404,"Repair compatibility profile not found.")
 sid=str(uuid.uuid4());now=utc_now()
 db.execute("""INSERT INTO diagnostic_sessions(session_id,device_id,profile_id,issue_summary,connection_method,state,findings,next_actions,created_at,updated_at)
 VALUES(?,?,?,?,?,?,?,?,?,?)""",(sid,p.device_id,p.profile_id,p.issue_summary,p.connection_method,"investigating",db.encode([]),db.encode([]),now,now))
 audit("repair.diagnostic.start","diagnostic_session",sid);return read_session(sid)
@router.get("/sessions")
def sessions():
 rows=db.many("SELECT session_id FROM diagnostic_sessions ORDER BY updated_at DESC LIMIT 200")
 return [read_session(r["session_id"]) for r in rows]
@router.get("/sessions/{session_id}")
def get_session(session_id:str):
 row=read_session(session_id)
 if not row:raise HTTPException(404,"Diagnostic session not found.")
 return row
@router.patch("/sessions/{session_id}")
def update_session(session_id:str,p:DiagnosticUpdate):
 row=read_session(session_id)
 if not row:raise HTTPException(404,"Diagnostic session not found.")
 if row["state"] in {"resolved","closed"}:raise HTTPException(409,"Closed diagnostic sessions cannot be changed.")
 db.execute("UPDATE diagnostic_sessions SET state=?,findings=?,next_actions=?,updated_at=? WHERE session_id=?",
  (p.state,db.encode(p.findings),db.encode(p.next_actions),utc_now(),session_id))
 audit("repair.diagnostic.update","diagnostic_session",session_id,p.state);return read_session(session_id)
