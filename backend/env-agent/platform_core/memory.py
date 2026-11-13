"""User-controlled, account-scoped memory notes. No automatic ingestion or model disclosure."""
import re,uuid
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now
from .identity import require_user
from .security import audit
router=APIRouter(prefix="/identity/v1/memory",tags=["J-ROC AI Personal Memory"])
_SECRET_PATTERN=re.compile(r"(?i)(api[_-]?key|access[_-]?token|password|client[_-]?secret)\\s*[:=]\\s*[^\\s,;]+|-----BEGIN [A-Z ]*PRIVATE KEY-----")
class MemoryInput(BaseModel):
 category:str=Field(min_length=2,max_length=60)
 title:str=Field(min_length=2,max_length=160)
 content:str=Field(min_length=1,max_length=8000)
 source:str=Field(default="user-entered",max_length=100)
def _safe_content(value):
 if _SECRET_PATTERN.search(value):raise HTTPException(422,"Memory notes must not contain credentials or private keys.")
 return value
@router.post("")
def create_memory(p:MemoryInput,user:dict=Depends(require_user)):
 content=_safe_content(p.content);memory_id=str(uuid.uuid4());now=utc_now()
 db.execute("INSERT INTO user_memory_items(memory_id,user_id,category,title,content,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
  (memory_id,user["user_id"],p.category,p.title,content,p.source,now,now))
 audit("memory.create","memory_item",memory_id,user["user_id"])
 return {"memory_id":memory_id,"category":p.category,"title":p.title,"content":content,"source":p.source,"created_at":now}
@router.get("")
def list_memory(category:str|None=None,q:str|None=Query(default=None,max_length=120),user:dict=Depends(require_user)):
 sql="SELECT memory_id,category,title,content,source,created_at,updated_at FROM user_memory_items WHERE user_id=?"
 values=[user["user_id"]]
 if category:sql+=" AND category=?";values.append(category)
 if q:
  sql+=" AND (title LIKE ? OR content LIKE ?)";values.extend(["%"+q+"%","%"+q+"%"])
 sql+=" ORDER BY updated_at DESC LIMIT 200"
 return db.many(sql,tuple(values))
@router.delete("/{memory_id}")
def delete_memory(memory_id:str,user:dict=Depends(require_user)):
 row=db.one("SELECT memory_id FROM user_memory_items WHERE memory_id=? AND user_id=?",(memory_id,user["user_id"]))
 if not row:raise HTTPException(404,"Memory item not found.")
 db.execute("DELETE FROM user_memory_items WHERE memory_id=? AND user_id=?",(memory_id,user["user_id"]))
 audit("memory.delete","memory_item",memory_id,user["user_id"])
 return {"memory_id":memory_id,"state":"deleted"}
