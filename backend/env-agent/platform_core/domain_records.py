"""Persistent domain records for Wave Four repair operations and Wave Five business services."""
import json
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from .database import db
from .models import utc_now
from .security import audit, require_platform_access

router=APIRouter(prefix="/platform/v1/domain",tags=["J-ROC AI Domain Services"],dependencies=[Depends(require_platform_access)])

DOMAINS={
 "repair_intelligence":31,"device_sessions":32,"diagnostics":33,"repair_workflows":34,
 "device_compatibility":35,"fleet_management":36,"update_orchestration":37,
 "service_history":38,"repair_reports":39,"repair_quality":40,
 "academy_courses":41,"tutor_sessions":42,"certifications":43,"customer_records":44,
 "commerce_catalog":45,"marketing_campaigns":46,"content_assets":47,"business_analytics":48,
 "support_cases":49,"asset_inventory":50
}
TERMINAL={"completed","cancelled","rejected","archived"}
ALLOWED_STATES={"draft","open","in_progress","awaiting_approval","approved","active","paused","completed","cancelled","rejected","archived"}
SENSITIVE_KEYS={"password","secret","token","api_key","apikey","access_key","private_key","authorization","credential"}

class DomainRecordCreate(BaseModel):
    model_config=ConfigDict(extra="forbid")
    title:str=Field(min_length=2,max_length=180)
    state:str=Field(default="open",pattern="^(draft|open|in_progress|awaiting_approval|approved|active|paused|completed|cancelled|rejected|archived)$")
    source_reference:str|None=Field(default=None,max_length=500)
    data:dict[str,Any]=Field(default_factory=dict)

class DomainRecordState(BaseModel):
    model_config=ConfigDict(extra="forbid")
    state:str=Field(pattern="^(draft|open|in_progress|awaiting_approval|approved|active|paused|completed|cancelled|rejected|archived)$")
    reason:str=Field(min_length=3,max_length=1000)

def _ensure():
    db.connect().execute("""CREATE TABLE IF NOT EXISTS domain_records(
      record_id TEXT PRIMARY KEY,domain TEXT NOT NULL,batch INTEGER NOT NULL,title TEXT NOT NULL,
      state TEXT NOT NULL,source_reference TEXT,data TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
    db.connect().execute("CREATE INDEX IF NOT EXISTS idx_domain_records ON domain_records(domain,state,updated_at)")

def _sanitize(value:Any):
    if isinstance(value,dict):
        return {str(k):_sanitize(v) for k,v in value.items() if str(k).lower().replace("-","_") not in SENSITIVE_KEYS and not any(word in str(k).lower() for word in ("password","secret","token","credential","private_key","api_key"))}
    if isinstance(value,list): return [_sanitize(v) for v in value[:500]]
    if isinstance(value,str): return value[:20000]
    if value is None or isinstance(value,(bool,int,float)): return value
    return str(value)[:2000]

def _domain(domain:str):
    if domain not in DOMAINS: raise HTTPException(404,"Domain service is not registered.")
    return DOMAINS[domain]

def _record(row):
    if row: row["data"]=db.decode(row["data"],{})
    return row

@router.get("/catalog")
def domain_catalog():
    return {"domains":[{"domain":name,"batch":batch,"record_api":True,"execution":"record-management-only"} for name,batch in DOMAINS.items()]}

@router.post("/{domain}/records")
def create_record(domain:str,item:DomainRecordCreate):
    batch=_domain(domain); _ensure()
    safe_data=_sanitize(item.data)
    if len(json.dumps(safe_data,ensure_ascii=False))>100000:
        raise HTTPException(413,"Record data exceeds the 100 kilobyte limit.")
    record_id=str(uuid.uuid4()); now=utc_now()
    db.execute("""INSERT INTO domain_records(record_id,domain,batch,title,state,source_reference,data,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?)""",(record_id,domain,batch,item.title,item.state,item.source_reference,db.encode(safe_data),now,now))
    audit("domain_record.create",domain,record_id,item.title)
    return _record(db.one("SELECT * FROM domain_records WHERE record_id=?",(record_id,)))

@router.get("/{domain}/records")
def list_records(domain:str,state:str|None=None,limit:int=Query(default=100,ge=1,le=500)):
    _domain(domain); _ensure()
    if state:
        if state not in ALLOWED_STATES: raise HTTPException(400,"Unsupported record state.")
        rows=db.many("SELECT * FROM domain_records WHERE domain=? AND state=? ORDER BY updated_at DESC LIMIT ?",(domain,state,limit))
    else:
        rows=db.many("SELECT * FROM domain_records WHERE domain=? ORDER BY updated_at DESC LIMIT ?",(domain,limit))
    return [_record(row) for row in rows]

@router.get("/{domain}/records/{record_id}")
def get_record(domain:str,record_id:str):
    _domain(domain); _ensure()
    row=_record(db.one("SELECT * FROM domain_records WHERE domain=? AND record_id=?",(domain,record_id)))
    if not row: raise HTTPException(404,"Domain record not found.")
    return row

@router.patch("/{domain}/records/{record_id}/state")
def update_record_state(domain:str,record_id:str,item:DomainRecordState):
    _domain(domain); _ensure()
    row=db.one("SELECT state FROM domain_records WHERE domain=? AND record_id=?",(domain,record_id))
    if not row: raise HTTPException(404,"Domain record not found.")
    if row["state"] in TERMINAL: raise HTTPException(409,"Terminal records cannot be reopened through this endpoint.")
    db.execute("UPDATE domain_records SET state=?,updated_at=? WHERE domain=? AND record_id=?",(item.state,utc_now(),domain,record_id))
    audit("domain_record.state",domain,record_id,item.reason)
    return get_record(domain,record_id)
