"""Inventory of explicitly registered devices; no silent device control."""
from .database import db
from .models import DeviceRegistration, utc_now
from .security import audit
class DeviceService:
    def register(self,item:DeviceRegistration):
        now=utc_now()
        db.execute("""INSERT INTO devices VALUES(?,?,?,?,?,?,?) ON CONFLICT(device_id) DO UPDATE SET display_name=excluded.display_name,device_type=excluded.device_type,connection_type=excluded.connection_type,capabilities=excluded.capabilities,state='detected',last_seen=excluded.last_seen""",(item.device_id,item.display_name,item.device_type,item.connection_type,db.encode(item.capabilities),"detected",now))
        audit("device.register","device",item.device_id,item.connection_type)
        return self.get(item.device_id)
    def get(self,device_id):
        row=db.one("SELECT * FROM devices WHERE device_id=?",(device_id,))
        if row: row["capabilities"]=db.decode(row["capabilities"],[])
        return row
    def list(self):
        rows=db.many("SELECT * FROM devices ORDER BY last_seen DESC")
        for row in rows: row["capabilities"]=db.decode(row["capabilities"],[])
        return rows
    def set_state(self,device_id,state):
        if state not in {"detected","authorized","disconnected","blocked"}: raise ValueError("Invalid device state")
        db.execute("UPDATE devices SET state=?,last_seen=? WHERE device_id=?",(state,utc_now(),device_id))
        audit("device.state","device",device_id,state)
        return self.get(device_id)
devices=DeviceService()
