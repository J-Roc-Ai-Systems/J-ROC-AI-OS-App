"""Small local knowledge index with source references and deterministic text matching."""
import hashlib, uuid
from .database import db
from .models import utc_now
from .security import audit
class KnowledgeService:
    def add(self,title,source_reference,content):
        if not title.strip() or not source_reference.strip() or not content.strip(): raise ValueError("Title, source and content are required")
        document_id=str(uuid.uuid4()); digest=hashlib.sha256(content.encode("utf-8")).hexdigest()
        db.execute("INSERT INTO knowledge_documents VALUES(?,?,?,?,?,?)",(document_id,title[:240],source_reference[:500],content[:100000],digest,utc_now()))
        audit("knowledge.add","document",document_id,source_reference)
        return {"document_id":document_id,"title":title,"source_reference":source_reference,"content_hash":digest}
    def search(self,query,limit=20):
        terms=[part.strip().lower() for part in query.split() if len(part.strip())>1][:8]
        if not terms: return []
        rows=db.many("SELECT document_id,title,source_reference,content,content_hash FROM knowledge_documents ORDER BY created_at DESC LIMIT 500")
        found=[]
        for row in rows:
            haystack=(row["title"]+" "+row["content"]).lower()
            score=sum(haystack.count(term) for term in terms)
            if score: found.append({"document_id":row["document_id"],"title":row["title"],"source_reference":row["source_reference"],"excerpt":row["content"][:600],"score":score})
        return sorted(found,key=lambda item:item["score"],reverse=True)[:max(1,min(limit,50))]
knowledge=KnowledgeService()
