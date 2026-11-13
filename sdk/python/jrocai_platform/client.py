"""Small standard-library client for the J-ROC AI shared platform API."""
from __future__ import annotations
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

class PlatformApiError(RuntimeError):
    def __init__(self,status:int,message:str):
        super().__init__(message); self.status=status

class JrocAiPlatformClient:
    def __init__(self,base_url:str,access_token:str,timeout:float=20):
        if not base_url.startswith("https://") and not base_url.startswith("http://127.0.0.1") and not base_url.startswith("http://localhost"):
            raise ValueError("Use HTTPS except for loopback development.")
        if not access_token: raise ValueError("A gateway access token is required.")
        self.base_url=base_url.rstrip("/")
        self.access_token=access_token
        self.timeout=timeout

    def request(self,method:str,path:str,payload=None):
        if not path.startswith("/") or ".." in path.split("/"): raise ValueError("Invalid API path.")
        body=None if payload is None else json.dumps(payload).encode("utf-8")
        headers={"Authorization":"Bearer "+self.access_token,"Accept":"application/json"}
        if body is not None: headers["Content-Type"]="application/json"
        request=Request(self.base_url+path,data=body,headers=headers,method=method.upper())
        try:
            with urlopen(request,timeout=self.timeout) as response:
                content=response.read()
                return json.loads(content.decode("utf-8")) if content else None
        except HTTPError as exc:
            message=exc.read(2048).decode("utf-8","replace")
            raise PlatformApiError(exc.code,message) from exc
        except URLError as exc:
            raise PlatformApiError(0,"J-ROC AI platform connection failed.") from exc

    def health(self): return self.request("GET","/health")
    def waves(self): return self.request("GET","/platform/v1/waves")
    def domain_catalog(self): return self.request("GET","/platform/v1/domain/catalog")
    def list_domain_records(self,domain:str,limit:int=100):
        return self.request("GET",f"/platform/v1/domain/{domain}/records?limit={max(1,min(limit,500))}")
    def create_domain_record(self,domain:str,title:str,data:dict,state:str="open",source_reference=None):
        return self.request("POST",f"/platform/v1/domain/{domain}/records",{"title":title,"data":data,"state":state,"source_reference":source_reference})
