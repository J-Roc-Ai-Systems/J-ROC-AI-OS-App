"""Wave Eleven through Fifteen: typed local-first platform service foundations."""
import json
import re
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from .database import db
from .models import utc_now
from .security import audit, require_platform_access

router = APIRouter(prefix="/platform/v1", tags=["J-ROC AI Waves Eleven to Fifteen"], dependencies=[Depends(require_platform_access)])

WAVES = [
 {"wave":11,"name":"Knowledge, data and intelligence services","batches":[(101,"Knowledge graph and entity registry"),(102,"Document ingestion and indexing"),(103,"Search and retrieval orchestration"),(104,"Data catalog and lineage"),(105,"Data quality and validation"),(106,"Analytics query workspace"),(107,"Reporting and dashboard services"),(108,"Research and evidence management"),(109,"Knowledge retention and lifecycle"),(110,"Intelligence evaluation and feedback")]},
 {"wave":12,"name":"Personal productivity and communications","batches":[(111,"Unified calendar and scheduling"),(112,"Tasks and project planning"),(113,"Notes and personal knowledge"),(114,"Email and message orchestration"),(115,"Meetings and transcription governance"),(116,"Notification preferences and delivery"),(117,"Contacts and relationship management"),(118,"Forms and approval workflows"),(119,"Personal automation recipes"),(120,"Accessibility and language preferences")]},
 {"wave":13,"name":"Finance and commerce operations","batches":[(121,"Business finance workspace"),(122,"Budget planning and controls"),(123,"Expense and reimbursement records"),(124,"Invoice lifecycle management"),(125,"Purchase order management"),(126,"Inventory and stock forecasting"),(127,"Order management and fulfillment"),(128,"Tax document organization"),(129,"Financial reconciliation and audit"),(130,"Revenue and margin analytics")]},
 {"wave":14,"name":"Creator studio and media production","batches":[(131,"Creative project management"),(132,"Audio production sessions"),(133,"Video production workflows"),(134,"Graphic and brand asset management"),(135,"Content calendar and publishing"),(136,"Media library and rights metadata"),(137,"Script and story development"),(138,"Podcast and broadcast production"),(139,"Audience engagement analytics"),(140,"Creator portfolio and licensing")]},
 {"wave":15,"name":"Infrastructure, reliability and platform governance","batches":[(141,"Infrastructure inventory and topology"),(142,"Service health and observability"),(143,"Incident response coordination"),(144,"Backup verification and recovery drills"),(145,"Configuration and change control"),(146,"Release health and rollback planning"),(147,"Capacity and performance management"),(148,"Security policy and evidence tracking"),(149,"Platform governance and risk register"),(150,"Operational readiness and certification")]}
]
BATCHES = {number:{"batch":number,"name":name,"wave":wave["wave"],"wave_name":wave["name"]} for wave in WAVES for number,name in wave["batches"]}
COLLECTIONS = {
 "knowledge_entities":101,"document_ingestions":102,"retrieval_queries":103,"data_catalog_entries":104,"data_quality_checks":105,"analytics_workspaces":106,"report_definitions":107,"research_cases":108,"knowledge_retention_rules":109,"intelligence_feedback":110,
 "calendar_items":111,"task_plans":112,"notes":113,"message_jobs":114,"meeting_records":115,"notification_preferences":116,"contact_records":117,"approval_forms":118,"automation_recipes":119,"accessibility_settings":120,
 "finance_workspaces":121,"budgets":122,"expense_records":123,"invoices":124,"purchase_orders":125,"inventory_forecasts":126,"fulfillment_orders":127,"tax_documents":128,"reconciliation_cases":129,"financial_reports":130,
 "creative_projects":131,"audio_sessions":132,"video_projects":133,"brand_assets":134,"publishing_items":135,"media_assets":136,"story_projects":137,"broadcast_sessions":138,"audience_reports":139,"creator_licenses":140,
 "infrastructure_assets":141,"service_observations":142,"incident_cases":143,"recovery_drills":144,"configuration_changes":145,"release_health_checks":146,"capacity_plans":147,"security_evidence":148,"governance_risks":149,"readiness_reviews":150
}
REQUIRED = {
 "knowledge_entities":("entity_type","canonical_name"),"document_ingestions":("source_reference","content_type"),"retrieval_queries":("query","search_scope"),"data_catalog_entries":("dataset_name","owner"),"data_quality_checks":("dataset_name","check_type"),"analytics_workspaces":("workspace_name","owner"),"report_definitions":("report_name","data_sources"),"research_cases":("question","evidence_sources"),"knowledge_retention_rules":("record_type","retention_days"),"intelligence_feedback":("subject","rating"),
 "calendar_items":("title","starts_at","timezone"),"task_plans":("objective","tasks"),"notes":("title","content"),"message_jobs":("channel","recipient_reference","message_reference"),"meeting_records":("title","starts_at"),"notification_preferences":("channel","enabled"),"contact_records":("display_name","relationship_type"),"approval_forms":("form_type","approver_reference"),"automation_recipes":("trigger","steps"),"accessibility_settings":("profile_id","preferences"),
 "finance_workspaces":("workspace_name","currency"),"budgets":("budget_name","amount","currency","period"),"expense_records":("amount","currency","category","occurred_at"),"invoices":("invoice_number","counterparty","amount","currency"),"purchase_orders":("order_number","supplier","items"),"inventory_forecasts":("sku","location","forecast_quantity"),"fulfillment_orders":("order_reference","items","destination_reference"),"tax_documents":("document_type","tax_year","source_reference"),"reconciliation_cases":("period","accounts","variance"),"financial_reports":("report_type","period","currency"),
 "creative_projects":("project_name","media_type","owner"),"audio_sessions":("project_reference","session_name","track_count"),"video_projects":("project_name","frame_size","frame_rate"),"brand_assets":("asset_name","asset_type","brand_reference"),"publishing_items":("title","channel","scheduled_at"),"media_assets":("asset_reference","media_type","rights_status"),"story_projects":("working_title","format","draft_reference"),"broadcast_sessions":("show_name","scheduled_at","platform"),"audience_reports":("channel","period","metrics"),"creator_licenses":("asset_reference","license_type","territory"),
 "infrastructure_assets":("asset_id","asset_type","environment"),"service_observations":("service_id","observed_at","status"),"incident_cases":("incident_type","severity","summary"),"recovery_drills":("system_reference","scenario","scheduled_at"),"configuration_changes":("system_reference","change_summary","requested_by"),"release_health_checks":("release_reference","checks"),"capacity_plans":("service_id","resource_type","target_capacity"),"security_evidence":("control_id","evidence_reference","collected_at"),"governance_risks":("risk_title","likelihood","impact","owner"),"readiness_reviews":("release_reference","criteria")
}
STATES={"draft","pending","awaiting_approval","approved","active","paused","completed","rejected","cancelled","archived"}
TERMINAL={"completed","rejected","cancelled","archived"}
SECRET_PARTS=("password","secret","token","credential","private_key","api_key","authorization","access_key")
BLOCKED_TERMS=("payment_capture","charge_card","execute_shell","arbitrary_code","secret_export","firmware_write","security_bypass")

class RecordCreate(BaseModel):
 model_config=ConfigDict(extra="forbid")
 title:str=Field(min_length=2,max_length=180)
 state:str=Field(default="draft",pattern="^(draft|pending|awaiting_approval|approved|active|paused|completed|rejected|cancelled|archived)$")
 source_reference:str|None=Field(default=None,max_length=500)
 data:dict[str,Any]=Field(default_factory=dict)

class RecordTransition(BaseModel):
 model_config=ConfigDict(extra="forbid")
 state:str=Field(pattern="^(draft|pending|awaiting_approval|approved|active|paused|completed|rejected|cancelled|archived)$")
 reason:str=Field(min_length=3,max_length=1000)

def _ensure():
 c=db.connect()
 c.execute("""CREATE TABLE IF NOT EXISTS wave1115_records(record_id TEXT PRIMARY KEY,collection TEXT NOT NULL,batch INTEGER NOT NULL,title TEXT NOT NULL,state TEXT NOT NULL,source_reference TEXT,data TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL)""")
 c.execute("CREATE INDEX IF NOT EXISTS idx_wave1115_collection ON wave1115_records(collection,state,updated_at)")

def _clean(value:Any):
 if isinstance(value,dict):
  return {str(k)[:100]:_clean(v) for k,v in value.items() if not any(term in str(k).lower() for term in SECRET_PARTS)}
 if isinstance(value,list):return [_clean(v) for v in value[:500]]
 if isinstance(value,str):return value[:20000]
 if value is None or isinstance(value,(bool,int,float)):return value
 return str(value)[:2000]

def _validate(collection:str,data:dict):
 missing=[field for field in REQUIRED[collection] if field not in data or data[field] in (None,"",[])]
 if missing:raise HTTPException(422,{"message":"Required collection fields are missing.","fields":missing})
 if any(term in json.dumps(data,ensure_ascii=False).lower() for term in BLOCKED_TERMS):
  raise HTTPException(403,"Requested operation is outside the approved platform boundary.")
 if collection in {"budgets","expense_records","invoices","financial_reports"}:
  amount=data.get("amount",0)
  if amount is not None and (not isinstance(amount,(int,float)) or isinstance(amount,bool) or amount<0):raise HTTPException(422,"Financial amounts must be non-negative numbers.")
 if collection=="budgets" and not re.fullmatch(r"[A-Z]{3}",str(data.get("currency",""))):raise HTTPException(422,"Currency must be a three-letter uppercase code.")
 if collection=="notification_preferences" and not isinstance(data.get("enabled"),bool):raise HTTPException(422,"Notification enabled must be a boolean.")
 if collection=="accessibility_settings" and not isinstance(data.get("preferences"),dict):raise HTTPException(422,"Accessibility preferences must be an object.")
 if collection=="automation_recipes":
  steps=data.get("steps")
  if not isinstance(steps,list) or not steps or len(steps)>30:raise HTTPException(422,"Automation recipes require one to thirty structured steps.")
  allowed={"notify","create_task","update_record","request_approval","webhook_reference"}
  if any(not isinstance(step,dict) or step.get("type") not in allowed for step in steps):raise HTTPException(403,"Automation step type is not allowlisted.")
 if collection=="media_assets" and data.get("rights_status") not in {"owned","licensed","public_domain","pending_review"}:raise HTTPException(422,"Media rights status must be explicitly classified.")
 if collection=="governance_risks":
  for key in ("likelihood","impact"):
   if not isinstance(data.get(key),int) or isinstance(data.get(key),bool) or not 1<=data[key]<=5:raise HTTPException(422,"Risk likelihood and impact must be integers from one to five.")
 if collection=="service_observations" and data.get("status") not in {"healthy","degraded","unavailable","unknown"}:raise HTTPException(422,"Unsupported service observation status.")
 if collection=="incident_cases" and data.get("severity") not in {"low","medium","high","critical"}:raise HTTPException(422,"Unsupported incident severity.")

def _record(row):
 if row:row["data"]=db.decode(row["data"],{})
 return row

@router.get("/waves/11-15")
def list_waves_eleven_to_fifteen():
 return {"waves":[{"wave":w["wave"],"name":w["name"],"batches":[{"batch":n,"name":name} for n,name in w["batches"]]} for w in WAVES],"wave_count":5,"batch_count":50,"first_batch":101,"last_batch":150,"collection_count":len(COLLECTIONS),"execution_boundary":"Validated records and approval states only; external actions require separately authorized workers.","spending_policy":"Zero-dollar by default; no payment capture."}

@router.get("/wave-eleven-fifteen/catalog")
def collection_catalog():
 return {"collections":[{"collection":name,"batch":batch,"required_fields":list(REQUIRED[name]),"record_api":True} for name,batch in COLLECTIONS.items()],"count":len(COLLECTIONS)}

@router.post("/wave-eleven-fifteen/records/{collection}")
def create_record(collection:str,item:RecordCreate):
 if collection not in COLLECTIONS:raise HTTPException(404,"Collection is not registered.")
 _ensure()
 safe=_clean(item.data);_validate(collection,safe)
 if len(json.dumps(safe,ensure_ascii=False))>100000:raise HTTPException(413,"Record data exceeds the 100 kilobyte limit.")
 rid=str(uuid.uuid4());now=utc_now()
 db.execute("INSERT INTO wave1115_records VALUES(?,?,?,?,?,?,?,?,?)",(rid,collection,COLLECTIONS[collection],item.title,item.state,item.source_reference,db.encode(safe),now,now))
 audit("wave1115_record.create",collection,rid,item.title)
 return _record(db.one("SELECT * FROM wave1115_records WHERE record_id=?",(rid,)))

@router.get("/wave-eleven-fifteen/records/{collection}")
def list_records(collection:str,state:str|None=None,limit:int=Query(default=100,ge=1,le=500)):
 if collection not in COLLECTIONS:raise HTTPException(404,"Collection is not registered.")
 if state and state not in STATES:raise HTTPException(400,"Unsupported record state.")
 _ensure()
 rows=db.many("SELECT * FROM wave1115_records WHERE collection=? AND state=? ORDER BY updated_at DESC LIMIT ?",(collection,state,limit)) if state else db.many("SELECT * FROM wave1115_records WHERE collection=? ORDER BY updated_at DESC LIMIT ?",(collection,limit))
 return [_record(row) for row in rows]

@router.get("/wave-eleven-fifteen/records/{collection}/{record_id}")
def get_record(collection:str,record_id:str):
 if collection not in COLLECTIONS:raise HTTPException(404,"Collection is not registered.")
 _ensure();row=_record(db.one("SELECT * FROM wave1115_records WHERE collection=? AND record_id=?",(collection,record_id)))
 if not row:raise HTTPException(404,"Record not found.")
 return row

@router.patch("/wave-eleven-fifteen/records/{collection}/{record_id}/state")
def transition_record(collection:str,record_id:str,item:RecordTransition):
 if collection not in COLLECTIONS:raise HTTPException(404,"Collection is not registered.")
 _ensure();row=db.one("SELECT state FROM wave1115_records WHERE collection=? AND record_id=?",(collection,record_id))
 if not row:raise HTTPException(404,"Record not found.")
 if row["state"] in TERMINAL:raise HTTPException(409,"Terminal records cannot be reopened.")
 if row["state"]=="awaiting_approval" and item.state=="active":raise HTTPException(409,"Approval is required before activation.")
 if row["state"]=="awaiting_approval" and item.state not in {"approved","rejected","cancelled"}:raise HTTPException(409,"An approval-pending record can only be approved, rejected, or cancelled.")
 db.execute("UPDATE wave1115_records SET state=?,updated_at=? WHERE collection=? AND record_id=?",(item.state,utc_now(),collection,record_id))
 audit("wave1115_record.transition",collection,record_id,item.reason)
 return get_record(collection,record_id)
