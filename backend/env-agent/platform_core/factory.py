"""Application factory project registry and safe project workspace creation."""
import re, uuid
from pathlib import Path
from .database import db
from .models import ProjectCreate, utc_now
from .security import audit

PROJECT_ROOT = Path(__import__("os").getenv("JROCAI_PROJECT_ROOT", "workspace/projects")).resolve()
_SLUG = re.compile(r"[^a-z0-9]+")
class FactoryService:
    def create(self, item: ProjectCreate):
        project_id=str(uuid.uuid4()); now=utc_now()
        db.execute("INSERT INTO projects VALUES(?,?,?,?,?,?,?,?)",(project_id,item.project_name,item.project_type,db.encode(item.target_platforms),item.description,"requested",now,now))
        audit("factory.project.create","project",project_id,item.project_type)
        return self.get(project_id)
    def get(self, project_id):
        row=db.one("SELECT * FROM projects WHERE project_id=?",(project_id,))
        if row: row["target_platforms"]=db.decode(row["target_platforms"],[])
        return row
    def list(self):
        rows=db.many("SELECT * FROM projects ORDER BY created_at DESC")
        for row in rows: row["target_platforms"]=db.decode(row["target_platforms"],[])
        return rows
    def prepare_workspace(self, project_id):
        project=self.get(project_id)
        if not project: return None
        slug=_SLUG.sub("-",project["project_name"].lower()).strip("-")[:48] or project_id[:8]
        target=(PROJECT_ROOT / (slug+"-"+project_id[:8])).resolve()
        if PROJECT_ROOT not in target.parents: raise ValueError("Unsafe project path")
        target.mkdir(parents=True,exist_ok=False)
        (target/"README.md").write_text("# "+project["project_name"]+"\n\nGenerated project workspace. Review the project plan before adding executable code.\n",encoding="utf-8")
        db.execute("UPDATE projects SET state='workspace_prepared',updated_at=? WHERE project_id=?",(utc_now(),project_id))
        audit("factory.workspace.prepare","project",project_id)
        return {"project_id":project_id,"workspace_reference":str(target.relative_to(PROJECT_ROOT)),"state":"workspace_prepared"}

factory=FactoryService()
