"""Application inventory; installation and removal require a separate platform-specific approval adapter."""
from .database import db
from .models import ApplicationRegistration, utc_now
from .security import audit
class ApplicationService:
    def register(self,item:ApplicationRegistration):
        now=utc_now()
        db.execute("""INSERT INTO applications VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(application_id) DO UPDATE SET display_name=excluded.display_name,version=excluded.version,platform=excluded.platform,package_reference=excluded.package_reference,state='registered',updated_at=excluded.updated_at""",(item.application_id,item.display_name,item.version,item.platform,item.package_reference,"registered",now,now))
        audit("application.register","application",item.application_id,item.platform)
        return self.get(item.application_id)
    def get(self,application_id): return db.one("SELECT * FROM applications WHERE application_id=?",(application_id,))
    def list(self): return db.many("SELECT * FROM applications ORDER BY display_name")
applications=ApplicationService()
