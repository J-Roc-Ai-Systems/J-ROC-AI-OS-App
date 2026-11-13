"""Integration registry. Stores secret references only, never credential values."""
from .database import db
from .models import IntegrationRegistration, utc_now
from .security import audit

class IntegrationService:
    def register(self, item: IntegrationRegistration):
        if item.secret_reference and not item.secret_reference.startswith("env-agent://"):
            raise ValueError("Credentials must be referenced through the Environment Agent.")
        now=utc_now()
        db.execute("""INSERT INTO integrations VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(integration_id) DO UPDATE SET display_name=excluded.display_name,integration_type=excluded.integration_type,provider=excluded.provider,capabilities=excluded.capabilities,secret_reference=excluded.secret_reference,updated_at=excluded.updated_at""",
          (item.integration_id,item.display_name,item.integration_type,item.provider,db.encode(item.capabilities),item.secret_reference,"pending_approval",now,now))
        audit("integration.register","integration",item.integration_id)
        return self.get(item.integration_id)
    def get(self, integration_id):
        row=db.one("SELECT * FROM integrations WHERE integration_id=?",(integration_id,))
        if row: row["capabilities"]=db.decode(row["capabilities"],[])
        return row
    def list(self):
        rows=db.many("SELECT * FROM integrations ORDER BY created_at")
        for row in rows: row["capabilities"]=db.decode(row["capabilities"],[])
        return rows
    def set_state(self, integration_id, state):
        if state not in {"pending_approval","approved","disabled","disconnected"}: raise ValueError("Invalid integration state")
        changed=db.execute("UPDATE integrations SET state=?,updated_at=? WHERE integration_id=?",(state,utc_now(),integration_id))
        if not changed: return None
        audit("integration.state","integration",integration_id,state)
        return self.get(integration_id)

integrations=IntegrationService()
