"""Persistent internal event bus and service registry."""
import uuid
from .database import db
from .models import utc_now
from .security import audit, redact

class PlatformEvents:
    def publish(self,event_type,source,payload):
        event_id=str(uuid.uuid4())
        db.execute("INSERT INTO platform_events(event_id,event_type,source,payload,created_at) VALUES(?,?,?,?,?)",(event_id,event_type[:100],source[:100],db.encode(payload),utc_now()))
        audit("event.publish","event",event_id,event_type)
        return {"event_id":event_id,"event_type":event_type,"source":source,"created_at":utc_now()}
    def list(self,limit=100):
        rows=db.many("SELECT * FROM platform_events ORDER BY created_at DESC LIMIT ?",(max(1,min(limit,500)),))
        for row in rows: row["payload"]=db.decode(row["payload"],{})
        return rows
    def register_service(self,service_id,display_name,version,capabilities):
        now=utc_now()
        db.execute("""INSERT INTO platform_services VALUES(?,?,?,?,?,?,?) ON CONFLICT(service_id) DO UPDATE SET display_name=excluded.display_name,version=excluded.version,capabilities=excluded.capabilities,state='registered',updated_at=excluded.updated_at""",(service_id,display_name,version,db.encode(capabilities),"registered",now,now))
        audit("service.register","service",service_id)
        return self.get_service(service_id)
    def get_service(self,service_id):
        row=db.one("SELECT * FROM platform_services WHERE service_id=?",(service_id,))
        if row: row["capabilities"]=db.decode(row["capabilities"],[])
        return row
    def services(self):
        rows=db.many("SELECT * FROM platform_services ORDER BY display_name")
        for row in rows: row["capabilities"]=db.decode(row["capabilities"],[])
        return rows

events=PlatformEvents()
