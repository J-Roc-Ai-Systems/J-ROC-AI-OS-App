"""Organization membership, fleet enrollment and policy registry foundations."""
import uuid
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now
from .security import require_platform_access,audit
from .identity import require_user
router=APIRouter(prefix="/platform/v1/enterprise",tags=["J-ROC AI Enterprise Operations"],dependencies=[Depends(require_platform_access)])
class OrganizationCreate(BaseModel):
 organization_id:str=Field(min_length=2,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
 name:str=Field(min_length=2,max_length=160)
 plan:str=Field(default="local",pattern=r"^(local|free|enterprise)$")
class MemberAdd(BaseModel):
 user_id:str=Field(min_length=2,max_length=80)
 role:str=Field(pattern=r"^(owner|administrator|operator|viewer)$")
class FleetDevice(BaseModel):
 device_id:str=Field(min_length=2,max_length=120)
 display_name:str=Field(min_length=2,max_length=120)
 platform:str=Field(min_length=2,max_length=40)
 manufacturer:str=Field(default="",max_length=100)
 model:str=Field(default="",max_length=120)
class Policy(BaseModel):
 policy_id:str=Field(min_length=2,max_length=80,pattern=r"^[a-zA-Z0-9._-]+$")
 name:str=Field(min_length=2,max_length=120)
 rules:dict=Field(default_factory=dict)
@router.post("/organizations")
def create_org(p:OrganizationCreate):
 now=utc_now()
 db.execute("INSERT INTO organizations(organization_id,name,plan,state,created_at,updated_at) VALUES(?,?,?,'active',?,?)",
  (p.organization_id,p.name,p.plan,now,now))
 audit("enterprise.organization.create","organization",p.organization_id)
 return db.one("SELECT * FROM organizations WHERE organization_id=?",(p.organization_id,))
@router.get("/organizations")
def organizations():return db.many("SELECT * FROM organizations ORDER BY created_at DESC")
@router.post("/organizations/{organization_id}/members")
def add_member(organization_id:str,p:MemberAdd):
 if not db.one("SELECT organization_id FROM organizations WHERE organization_id=?",(organization_id,)):raise HTTPException(404,"Organization not found.")
 if not db.one("SELECT user_id FROM platform_users WHERE user_id=?",(p.user_id,)):raise HTTPException(404,"User not found.")
 db.execute("""INSERT INTO organization_members(organization_id,user_id,role,state,created_at)
 VALUES(?,?,?,'active',?) ON CONFLICT(organization_id,user_id) DO UPDATE SET role=excluded.role,state='active'""",
  (organization_id,p.user_id,p.role,utc_now()))
 audit("enterprise.member.add","organization",organization_id,p.user_id)
 return {"organization_id":organization_id,"user_id":p.user_id,"role":p.role}
@router.get("/organizations/{organization_id}/members")
def members(organization_id:str):
 return db.many("SELECT m.user_id,u.email,u.display_name,m.role,m.state,m.created_at FROM organization_members m JOIN platform_users u ON u.user_id=m.user_id WHERE m.organization_id=? ORDER BY m.created_at",(organization_id,))
@router.post("/organizations/{organization_id}/devices")
def enroll_device(organization_id:str,p:FleetDevice):
 if not db.one("SELECT organization_id FROM organizations WHERE organization_id=?",(organization_id,)):raise HTTPException(404,"Organization not found.")
 now=utc_now();enrollment_id=str(uuid.uuid4())
 db.execute("""INSERT INTO fleet_enrollments(enrollment_id,organization_id,device_id,display_name,platform,manufacturer,model,state,enrolled_at,updated_at)
 VALUES(?,?,?,?,?,?,?,'pending_approval',?,?)""",(enrollment_id,organization_id,p.device_id,p.display_name,p.platform,p.manufacturer,p.model,now,now))
 audit("enterprise.device.enroll","fleet_device",p.device_id,organization_id)
 return db.one("SELECT * FROM fleet_enrollments WHERE enrollment_id=?",(enrollment_id,))
@router.get("/organizations/{organization_id}/devices")
def fleet_devices(organization_id:str):
 return db.many("SELECT * FROM fleet_enrollments WHERE organization_id=? ORDER BY enrolled_at DESC",(organization_id,))
@router.post("/policies")
def create_policy(p:Policy):
 now=utc_now()
 db.execute("""INSERT INTO device_policies(policy_id,name,rules,enabled,created_at,updated_at) VALUES(?,?,?,1,?,?)
 ON CONFLICT(policy_id) DO UPDATE SET name=excluded.name,rules=excluded.rules,enabled=1,updated_at=excluded.updated_at""",
 (p.policy_id,p.name,db.encode(p.rules),now,now))
 audit("enterprise.policy.create","device_policy",p.policy_id)
 return {"policy_id":p.policy_id,"name":p.name,"rules":p.rules,"enabled":True}
@router.get("/policies")
def policies():
 rows=db.many("SELECT * FROM device_policies ORDER BY name")
 for row in rows:row["rules"]=db.decode(row["rules"],{})
 return rows


# Account-session routes enforce organization membership instead of relying on
# the shared gateway administrator credential.
user_router=APIRouter(prefix="/identity/v1/enterprise",tags=["J-ROC AI Tenant Operations"])
def _membership(organization_id:str,user:dict,allowed_roles:set[str]|None=None):
 row=db.one("SELECT role,state FROM organization_members WHERE organization_id=? AND user_id=?",(organization_id,user["user_id"]))
 if not row or row["state"]!="active":raise HTTPException(403,"Active organization membership is required.")
 if allowed_roles and row["role"] not in allowed_roles:raise HTTPException(403,"Your organization role cannot perform this action.")
 return row
@user_router.get("/organizations")
def my_organizations(user:dict=Depends(require_user)):
 return db.many("""SELECT o.organization_id,o.name,o.plan,o.state,m.role,m.created_at AS joined_at
 FROM organization_members m JOIN organizations o ON o.organization_id=m.organization_id
 WHERE m.user_id=? AND m.state='active' ORDER BY o.name""",(user["user_id"],))
@user_router.get("/organizations/{organization_id}/members")
def my_organization_members(organization_id:str,user:dict=Depends(require_user)):
 _membership(organization_id,user)
 return db.many("""SELECT m.user_id,u.display_name,m.role,m.state,m.created_at
 FROM organization_members m JOIN platform_users u ON u.user_id=m.user_id
 WHERE m.organization_id=? AND m.state='active' ORDER BY m.created_at""",(organization_id,))
@user_router.get("/organizations/{organization_id}/devices")
def my_organization_devices(organization_id:str,user:dict=Depends(require_user)):
 _membership(organization_id,user)
 return db.many("SELECT enrollment_id,device_id,display_name,platform,manufacturer,model,state,enrolled_at,updated_at FROM fleet_enrollments WHERE organization_id=? ORDER BY enrolled_at DESC",(organization_id,))
@user_router.post("/organizations/{organization_id}/devices")
def member_enroll_device(organization_id:str,p:FleetDevice,user:dict=Depends(require_user)):
 _membership(organization_id,user,{"owner","administrator","operator"})
 now=utc_now();enrollment_id=str(uuid.uuid4())
 db.execute("""INSERT INTO fleet_enrollments(enrollment_id,organization_id,device_id,display_name,platform,manufacturer,model,state,enrolled_at,updated_at)
 VALUES(?,?,?,?,?,?,?,'pending_approval',?,?)""",(enrollment_id,organization_id,p.device_id,p.display_name,p.platform,p.manufacturer,p.model,now,now))
 audit("enterprise.device.enroll","fleet_device",p.device_id,organization_id)
 return db.one("SELECT * FROM fleet_enrollments WHERE enrollment_id=?",(enrollment_id,))
