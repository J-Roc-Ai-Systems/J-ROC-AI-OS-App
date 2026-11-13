"""Permanent read-only GitHub Source Agent for the J-ROC AI platform."""
import base64
import os
import re
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
import httpx
from .security import require_platform_access

router=APIRouter(prefix="/platform/v1/source-agent",tags=["J-ROC AI Source Agent"],dependencies=[Depends(require_platform_access)])
_GITHUB_API="https://api.github.com"
_REPOSITORY_PART=re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
_REF=re.compile(r"^[A-Za-z0-9_./-]{1,200}$")

def validate_repository(owner:str,repo:str):
 if not _REPOSITORY_PART.fullmatch(owner) or not _REPOSITORY_PART.fullmatch(repo) or ".." in owner or ".." in repo:
  raise HTTPException(422,"Repository owner or name is invalid.")
 return owner,repo

def validate_source_path(path:str):
 normalized=path.replace("\\","/")
 if normalized.startswith("/") or any(part in {".",".."} for part in normalized.split("/")) or len(normalized)>500:
  raise HTTPException(422,"Repository path is invalid.")
 return normalized

def _headers():
 token=os.getenv("JROCAI_GITHUB_READ_TOKEN") or os.getenv("GITHUB_TOKEN") or ""
 headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"J-ROC-AI-Source-Agent"}
 if token:headers["Authorization"]="Bearer "+token
 return headers

async def _get(path:str,params:dict|None=None):
 try:
  async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
   response=await client.get(_GITHUB_API+path,headers=_headers(),params=params)
 except httpx.HTTPError:
  raise HTTPException(502,"GitHub read request could not be completed.")
 if response.status_code==404:raise HTTPException(404,"GitHub repository resource was not found or is not accessible.")
 if response.status_code==403:raise HTTPException(503,"GitHub denied the read request or its rate limit was reached.")
 if response.status_code>=400:raise HTTPException(502,"GitHub returned an unsuccessful read response.")
 return response.json()

@router.get("/status")
def source_agent_status():
 return {"agent_id":"source-agent","name":"J-ROC AI Source Agent","scope":"read_only","github_token_configured":bool(os.getenv("JROCAI_GITHUB_READ_TOKEN") or os.getenv("GITHUB_TOKEN")),"writes_enabled":False,"supported_operations":["repository_metadata","repository_tree","read_file"],"secret_values_returned":False}

@router.get("/repositories/{owner}/{repo}")
async def repository_metadata(owner:str,repo:str):
 validate_repository(owner,repo)
 data=await _get("/repos/"+owner+"/"+repo)
 return {"full_name":data.get("full_name"),"private":data.get("private"),"default_branch":data.get("default_branch"),"html_url":data.get("html_url"),"archived":data.get("archived"),"permissions":data.get("permissions")}

@router.get("/repositories/{owner}/{repo}/tree")
async def repository_tree(owner:str,repo:str,ref:str=Query(default="HEAD",min_length=1,max_length=200),path:str=""):
 validate_repository(owner,repo)
 if not _REF.fullmatch(ref) or ".." in ref.split("/"):raise HTTPException(422,"Git reference is invalid.")
 normalized=validate_source_path(path) if path else ""
 data=await _get("/repos/"+owner+"/"+repo+"/git/trees/"+quote(ref,safe="/"),{"recursive":"1"})
 entries=data.get("tree",[])
 if normalized:entries=[entry for entry in entries if entry.get("path","").startswith(normalized.rstrip("/")+"/") or entry.get("path")==normalized]
 return {"repository":owner+"/"+repo,"ref":ref,"truncated":bool(data.get("truncated")),"count":len(entries),"entries":[{"path":e.get("path"),"type":e.get("type"),"size":e.get("size"),"sha":e.get("sha")} for e in entries[:5000]]}

@router.get("/repositories/{owner}/{repo}/files")
async def read_repository_file(owner:str,repo:str,path:str=Query(min_length=1,max_length=500),ref:str=Query(default="HEAD",min_length=1,max_length=200)):
 validate_repository(owner,repo)
 normalized=validate_source_path(path)
 if not normalized:raise HTTPException(422,"A file path is required.")
 if not _REF.fullmatch(ref) or ".." in ref.split("/"):raise HTTPException(422,"Git reference is invalid.")
 data=await _get("/repos/"+owner+"/"+repo+"/contents/"+quote(normalized,safe="/"),{"ref":ref})
 if data.get("type")!="file":raise HTTPException(400,"Requested repository path is not a file.")
 if int(data.get("size") or 0)>1_000_000:raise HTTPException(413,"Source file exceeds the one megabyte read limit.")
 encoded=data.get("content","")
 try:content=base64.b64decode(encoded,validate=False).decode("utf-8")
 except (ValueError,UnicodeDecodeError):raise HTTPException(415,"Source file is not valid UTF-8 text.")
 return {"repository":owner+"/"+repo,"path":normalized,"ref":ref,"size":len(content.encode("utf-8")),"sha":data.get("sha"),"content":content[:1_000_000],"read_only":True}
