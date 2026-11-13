"""Persistent in-app notification center."""
from .database import db
from .models import utc_now
from .security import audit, redact
class CommunicationService:
    def publish(self,category,title,message,severity="info"):
        if severity not in {"info","success","warning","critical"}: raise ValueError("Invalid severity")
        title=redact(title); message=redact(message)
        notification_id=db.execute("INSERT INTO notifications(category,title,message,severity,created_at) VALUES(?,?,?,?,?)",(category[:60],title[:160],message[:2000],severity,utc_now()))
        audit("notification.publish","notification",str(notification_id),severity)
        return self.get(notification_id)
    def get(self,notification_id): return db.one("SELECT * FROM notifications WHERE notification_id=?",(notification_id,))
    def list(self,unread_only=False,limit=100):
        sql="SELECT * FROM notifications"
        if unread_only: sql+=" WHERE read_at IS NULL"
        return db.many(sql+" ORDER BY created_at DESC LIMIT ?",(max(1,min(limit,200)),))
    def mark_read(self,notification_id):
        db.execute("UPDATE notifications SET read_at=? WHERE notification_id=?",(utc_now(),notification_id))
        return self.get(notification_id)
communications=CommunicationService()
