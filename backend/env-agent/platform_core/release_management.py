"""Release channels and approval gates. This registry does not deploy binaries."""
import uuid
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now
from .security import require_platform_access,audit
router=APIRouter(prefix="/platform/v1/releases",tags=["J-ROC AI Release Management"],dependencies=[Depends(require_platform_access)])
class Channel(BaseModel):
 channel_id:str=Field(min_length=2,max_length=60,pattern=r"^[a-zA-Z0-9._-]+$")
 name:str=Field(min_length=2,max_length=100)
 stability:str=Field(pattern=r"^(development|preview|stable|long_term_support)$")
class ReleaseCreate(BaseModel):
 release_id:str=Field(min_length=2,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
 application_id:str=Field(min_length=2,max_length=100)
 version:str=Field(min_length=1,max_length=40)
 channel_id:str=Field(min_length=2,max_length=60)
 artifact_reference:str=Field(min_length=1,max_length=500)
 source_revision:str=Field(min_length=7,max_length=80)
 notes:str=Field(default="",max_length=4000)
@router.post("/channels")
def create_channel(p:Channel):
 now=utc_now()
 db.execute("""INSERT INTO release_channels(channel_id,name,stability,created_at,updated_at) VALUES(?,?,?,?,?)
 ON CONFLICT(channel_id) DO UPDATE SET name=excluded.name,stability=excluded.stability,updated_at=excluded.updated_at""",
 (p.channel_id,p.name,p.stability,now,now))
 audit("release.channel.create","release_channel",p.channel_id)
 return db.one("SELECT * FROM release_channels WHERE channel_id=?",(p.channel_id,))
@router.get("/channels")
def channels():return db.many("SELECT * FROM release_channels ORDER BY name")
@router.post("")
def create_release(p:ReleaseCreate):
 if not db.one("SELECT channel_id FROM release_channels WHERE channel_id=?",(p.channel_id,)):raise HTTPException(404,"Release channel not found.")
 if not db.one("SELECT application_id FROM applications WHERE application_id=?",(p.application_id,)):raise HTTPException(404,"Application not found.")
 now=utc_now()
 db.execute("""INSERT INTO releases(release_id,application_id,version,channel_id,artifact_reference,source_revision,notes,state,created_at,updated_at)
 VALUES(?,?,?,?,?,?,?,'pending_approval',?,?)""",(p.release_id,p.application_id,p.version,p.channel_id,p.artifact_reference,p.source_revision,p.notes,now,now))
 audit("release.create","release",p.release_id)
 return db.one("SELECT * FROM releases WHERE release_id=?",(p.release_id,))
@router.get("")
def releases():return db.many("SELECT * FROM releases ORDER BY created_at DESC LIMIT 200")
@router.post("/{release_id}/approve")
def approve(release_id:str):
 row=db.one("SELECT * FROM releases WHERE release_id=?",(release_id,))
 if not row:raise HTTPException(404,"Release not found.")
 if row["state"]!="pending_approval":raise HTTPException(409,"Release is not awaiting approval.")
 db.execute("UPDATE releases SET state='approved',updated_at=? WHERE release_id=?",(utc_now(),release_id))
 db.execute("INSERT INTO release_approvals(approval_id,release_id,decision,reviewer,created_at) VALUES(?,?, 'approved','gateway-administrator',?)",
  (str(uuid.uuid4()),release_id,utc_now()))
 audit("release.approve","release",release_id)
 return db.one("SELECT * FROM releases WHERE release_id=?",(release_id,))
@router.post("/{release_id}/publish")
def publish(release_id:str):
 row=db.one("SELECT * FROM releases WHERE release_id=?",(release_id,))
 if not row:raise HTTPException(404,"Release not found.")
 if row["state"]!="approved":raise HTTPException(409,"Only approved releases can be marked ready.")
 db.execute("UPDATE releases SET state='ready_for_distribution',updated_at=? WHERE release_id=?",(utc_now(),release_id))
 audit("release.ready","release",release_id,"No deployment was performed.")
 return db.one("SELECT * FROM releases WHERE release_id=?",(release_id,))
