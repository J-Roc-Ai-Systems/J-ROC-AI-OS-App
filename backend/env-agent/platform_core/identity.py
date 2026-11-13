"""Local-first account identity with hashed, expiring sessions."""
import hashlib,hmac,secrets,uuid
from datetime import datetime,timedelta,timezone
import os
from fastapi import APIRouter,Depends,Header,HTTPException,Request
from pydantic import BaseModel,Field
from .database import db
from .models import utc_now
from .security import require_platform_access,audit
router=APIRouter(prefix="/identity/v1",tags=["J-ROC AI Identity"])
admin_router=APIRouter(prefix="/identity/v1/admin",tags=["J-ROC AI Identity Administration"],dependencies=[Depends(require_platform_access)])
class RegisterRequest(BaseModel):
 email:str=Field(min_length=5,max_length=254)
 display_name:str=Field(min_length=2,max_length=100)
 password:str=Field(min_length=12,max_length=256)
class LoginRequest(BaseModel):
 email:str=Field(min_length=5,max_length=254)
 password:str=Field(min_length=1,max_length=256)
class RoleUpdate(BaseModel):
 role:str=Field(pattern=r"^(chairman|administrator|operator|worker|member)$")
def _hash_password(password,salt=None):
 salt=salt or secrets.token_bytes(16)
 digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,310000)
 return "pbkdf2_sha256$310000$"+salt.hex()+"$"+digest.hex()
def _verify_password(password,encoded):
 try:
  algorithm,rounds,salt_hex,digest_hex=encoded.split("$",3)
  if algorithm!="pbkdf2_sha256" or int(rounds)!=310000:return False
  actual=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt_hex),int(rounds))
  return hmac.compare_digest(actual,bytes.fromhex(digest_hex))
 except (ValueError,TypeError):return False
def _session(user):
 token=secrets.token_urlsafe(48); now=datetime.now(timezone.utc); expires=now+timedelta(hours=12)
 db.execute("INSERT INTO user_sessions(session_id,user_id,token_hash,expires_at,created_at) VALUES(?,?,?,?,?)",
  (str(uuid.uuid4()),user["user_id"],hashlib.sha256(token.encode()).hexdigest(),expires.isoformat(),now.isoformat()))
 return {"access_token":token,"token_type":"Bearer","expires_at":expires.isoformat(),
  "user":{k:user[k] for k in ("user_id","email","display_name","role")}}
def require_user(authorization:str|None=Header(default=None)):
 token=(authorization or "").removeprefix("Bearer ").strip()
 if not token:raise HTTPException(401,"User session required.")
 row=db.one("""SELECT u.user_id,u.email,u.display_name,u.role,u.state,s.session_id,s.expires_at
 FROM user_sessions s JOIN platform_users u ON u.user_id=s.user_id WHERE s.token_hash=? AND s.revoked_at IS NULL""",
  (hashlib.sha256(token.encode()).hexdigest(),))
 if not row or row["state"]!="active":raise HTTPException(401,"User session is invalid.")
 if row["expires_at"]<=utc_now():raise HTTPException(401,"User session has expired.")
 return row
@router.post("/register")
def register(payload:RegisterRequest):
 email=payload.email.strip().lower()
 if "@" not in email or "." not in email.rsplit("@",1)[-1]:raise HTTPException(422,"A valid email address is required.")
 user_id=str(uuid.uuid4()); now=utc_now()
 try:
  db.execute("INSERT INTO platform_users(user_id,email,display_name,password_hash,role,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
   (user_id,email,payload.display_name.strip(),_hash_password(payload.password),"member","active",now,now))
 except Exception as exc:
  if "UNIQUE" in str(exc).upper():raise HTTPException(409,"An account with this email already exists.")
  raise
 user=db.one("SELECT user_id,email,display_name,role FROM platform_users WHERE user_id=?",(user_id,))
 audit("identity.register","user",user_id)
 return _session(user)
@router.post("/login")
def login(payload:LoginRequest,request:Request):
 email=payload.email.strip().lower()
 remote=request.client.host if request.client else "unknown"
 ip_hash=hashlib.sha256(remote.encode()).hexdigest()
 now=datetime.now(timezone.utc)
 attempt=db.one("SELECT * FROM identity_login_attempts WHERE email=? AND ip_hash=?",(email,ip_hash))
 if attempt and attempt["locked_until"] and attempt["locked_until"]>now.isoformat():
  raise HTTPException(429,"Too many failed sign-in attempts. Try again later.")
 user=db.one("SELECT * FROM platform_users WHERE email=? COLLATE NOCASE",(email,))
 valid=bool(user and user["state"]=="active" and _verify_password(payload.password,user["password_hash"]))
 if not valid:
  window_start=now
  count=1
  if attempt:
   try:
    previous=datetime.fromisoformat(attempt["window_started_at"])
    if now-previous<timedelta(minutes=15):
     window_start=previous
     count=attempt["failed_count"]+1
   except ValueError:pass
  locked=(now+timedelta(minutes=15)).isoformat() if count>=5 else None
  db.execute("""INSERT INTO identity_login_attempts(email,ip_hash,failed_count,window_started_at,locked_until)
   VALUES(?,?,?,?,?) ON CONFLICT(email,ip_hash) DO UPDATE SET failed_count=excluded.failed_count,
   window_started_at=excluded.window_started_at,locked_until=excluded.locked_until""",
   (email,ip_hash,count,window_start.isoformat(),locked))
  audit("identity.login.failed","account",hashlib.sha256(email.encode()).hexdigest())
  raise HTTPException(401,"Email or password is incorrect.")
 db.execute("DELETE FROM identity_login_attempts WHERE email=? AND ip_hash=?",(email,ip_hash))
 audit("identity.login","user",user["user_id"])
 return _session(user)
@router.get("/me")
def me(user:dict=Depends(require_user)):return {k:user[k] for k in ("user_id","email","display_name","role")}
@router.post("/logout")
def logout(user:dict=Depends(require_user)):
 db.execute("UPDATE user_sessions SET revoked_at=? WHERE session_id=?",(utc_now(),user["session_id"]))
 audit("identity.logout","user",user["user_id"]);return {"session_state":"revoked"}
@admin_router.get("/users")
def list_users(limit:int=100):
 return db.many("SELECT user_id,email,display_name,role,state,created_at,updated_at FROM platform_users ORDER BY created_at DESC LIMIT ?",(max(1,min(limit,200)),))

@admin_router.patch("/users/{user_id}/role")
def update_user_role(user_id:str,payload:RoleUpdate):
 if not db.one("SELECT user_id FROM platform_users WHERE user_id=?",(user_id,)):
  raise HTTPException(404,"User not found.")
 if payload.role=="chairman" and os.getenv("JROCAI_ALLOW_CHAIRMAN_ROLE_ASSIGNMENT","false").lower()!="true":
  raise HTTPException(403,"Chairman role assignment is disabled in the Environment Agent.")
 db.execute("UPDATE platform_users SET role=?,updated_at=? WHERE user_id=?",(payload.role,utc_now(),user_id))
 audit("identity.role.change","user",user_id,payload.role)
 return db.one("SELECT user_id,email,display_name,role,state,created_at,updated_at FROM platform_users WHERE user_id=?",(user_id,))
