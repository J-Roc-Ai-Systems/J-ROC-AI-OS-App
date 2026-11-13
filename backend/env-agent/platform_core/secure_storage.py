"""Authenticated, encrypted file storage using an Environment Agent managed key."""
import base64,hashlib,os,uuid
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now
from .identity import require_user
from .security import audit
router=APIRouter(prefix="/identity/v1/files",tags=["J-ROC AI Encrypted File Storage"])
MAX_FILE_BYTES=5*1024*1024
ROOT=Path(os.getenv("JROCAI_ENCRYPTED_FILE_ROOT","data/encrypted-files")).resolve()
def _cipher():
 raw=os.getenv("JROCAI_FILE_ENCRYPTION_KEY","")
 if not raw:raise HTTPException(503,"Encrypted file storage is not configured in the Environment Agent.")
 try:key=base64.urlsafe_b64decode(raw+"="*((4-len(raw)%4)%4))
 except Exception:raise HTTPException(503,"Encrypted file storage key is invalid.")
 if len(key)!=32:raise HTTPException(503,"Encrypted file storage key must decode to 32 bytes.")
 return AESGCM(key)
class Upload(BaseModel):
 name:str=Field(min_length=1,max_length=180)
 content_type:str=Field(default="application/octet-stream",max_length=120)
 content_base64:str=Field(min_length=4,max_length=MAX_FILE_BYTES*2)
@router.post("")
def upload(p:Upload,user:dict=Depends(require_user)):
 try:data=base64.b64decode(p.content_base64,validate=True)
 except Exception:raise HTTPException(422,"File content must be valid Base64.")
 if not data or len(data)>MAX_FILE_BYTES:raise HTTPException(413,"File is empty or exceeds the 5 MiB limit.")
 file_id=str(uuid.uuid4());nonce=os.urandom(12);cipher=_cipher()
 encrypted=cipher.encrypt(nonce,data,file_id.encode())
 ROOT.mkdir(parents=True,exist_ok=True)
 path=ROOT/(file_id+".blob")
 path.write_bytes(encrypted)
 digest=hashlib.sha256(encrypted).hexdigest();now=utc_now()
 db.execute("""INSERT INTO encrypted_files(file_id,owner_id,name,content_type,encrypted_path,nonce,cipher_hash,plain_size,created_at)
 VALUES(?,?,?,?,?,?,?,?,?)""",(file_id,user["user_id"],Path(p.name).name,p.content_type,str(path),base64.b64encode(nonce).decode(),digest,len(data),now))
 audit("file.upload","encrypted_file",file_id,user["user_id"])
 return {"file_id":file_id,"name":Path(p.name).name,"content_type":p.content_type,"size_bytes":len(data),"encrypted":True,"created_at":now}
@router.get("")
def list_files(user:dict=Depends(require_user)):
 return db.many("SELECT file_id,name,content_type,plain_size AS size_bytes,created_at FROM encrypted_files WHERE owner_id=? ORDER BY created_at DESC",(user["user_id"],))
@router.get("/{file_id}")
def download(file_id:str,user:dict=Depends(require_user)):
 row=db.one("SELECT * FROM encrypted_files WHERE file_id=? AND owner_id=?",(file_id,user["user_id"]))
 if not row:raise HTTPException(404,"File not found.")
 path=Path(row["encrypted_path"]).resolve()
 if not path.is_relative_to(ROOT) or not path.is_file():raise HTTPException(404,"Encrypted file data is unavailable.")
 encrypted=path.read_bytes()
 if not hashlib.sha256(encrypted).hexdigest()==row["cipher_hash"]:raise HTTPException(409,"Encrypted file integrity check failed.")
 try:
  plain=_cipher().decrypt(base64.b64decode(row["nonce"]),encrypted,file_id.encode())
 except Exception:raise HTTPException(409,"File decryption failed.")
 return {"file_id":file_id,"name":row["name"],"content_type":row["content_type"],"content_base64":base64.b64encode(plain).decode()}
@router.delete("/{file_id}")
def delete_file(file_id:str,user:dict=Depends(require_user)):
 row=db.one("SELECT encrypted_path FROM encrypted_files WHERE file_id=? AND owner_id=?",(file_id,user["user_id"]))
 if not row:raise HTTPException(404,"File not found.")
 path=Path(row["encrypted_path"]).resolve()
 if path.is_relative_to(ROOT) and path.is_file():path.unlink()
 db.execute("DELETE FROM encrypted_files WHERE file_id=? AND owner_id=?",(file_id,user["user_id"]))
 audit("file.delete","encrypted_file",file_id,user["user_id"])
 return {"file_id":file_id,"state":"deleted"}
