"""Local-only Ollama adapter. No cloud fallback or remote model endpoint."""
import os
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from .security import require_platform_access
router=APIRouter(prefix="/platform/v1/local-models",tags=["J-ROC AI Local Model Router"],dependencies=[Depends(require_platform_access)])
def local_url():
 value=os.getenv("JROCAI_LOCAL_MODEL_BASE_URL","http://127.0.0.1:11434").rstrip("/")
 parsed=urlparse(value)
 if parsed.scheme!="http" or parsed.hostname not in {"127.0.0.1","localhost","::1"}:
  raise HTTPException(503,"Local model endpoint must be an HTTP loopback address.")
 return value
class Chat(BaseModel):
 model:str=Field(min_length=1,max_length=120)
 message:str=Field(min_length=1,max_length=12000)
 system:str=Field(default="You are J-ROC AI, a helpful local assistant.",max_length=4000)
@router.get("/status")
async def status():
 try:
  async with httpx.AsyncClient(timeout=3) as client:r=await client.get(local_url()+"/api/tags")
  r.raise_for_status();names=[m.get("name") for m in r.json().get("models",[]) if m.get("name")]
  return {"available":True,"provider":"ollama-local","models":names,"cloud_fallback":False}
 except HTTPException:raise
 except (httpx.HTTPError,ValueError):return {"available":False,"provider":"ollama-local","models":[],"cloud_fallback":False}
@router.post("/chat")
async def chat(payload:Chat):
 body={"model":payload.model,"stream":False,"messages":[{"role":"system","content":payload.system},{"role":"user","content":payload.message}]}
 try:
  async with httpx.AsyncClient(timeout=120) as client:r=await client.post(local_url()+"/api/chat",json=body)
  r.raise_for_status();answer=r.json().get("message",{}).get("content","")
  if not answer:raise HTTPException(502,"Local model returned no message.")
  return {"reply":answer,"model":payload.model,"provider":"ollama-local","cloud_fallback":False}
 except httpx.TimeoutException:raise HTTPException(504,"Local model timed out; no cloud fallback was attempted.")
 except httpx.HTTPError:raise HTTPException(502,"Local model is unavailable; no cloud fallback was attempted.")
