"""J-ROC AI Env Agent: server-side secret boundary and authenticated provider gateway.

Provider credentials are read only from the backend process environment. Secret values are never returned.
"""
import hmac
import os
from typing import Literal
import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="J-ROC AI Env Agent", version="0.3.0")
from platform_core.api import router as platform_router
app.include_router(platform_router)
from platform_core.wave345 import router as waves_three_to_five_router
app.include_router(waves_three_to_five_router)
from platform_core.domain_records import router as domain_records_router
app.include_router(domain_records_router)
from platform_core.wave610 import router as waves_six_to_ten_router
app.include_router(waves_six_to_ten_router)

@app.on_event("startup")
def register_wave_two_services():
    from platform_core.events import events
    services = [
        ("application-factory", "Application Factory", ["project-registration", "workspace-preparation"]),
        ("artificial-intelligence-brain", "Artificial Intelligence Brain", ["local-planning", "spending-policy"]),
        ("integration-registry", "Integration Registry", ["connection-registration", "secret-references"]),
        ("production-workers", "Production Worker System", ["worker-registry", "durable-jobs", "worker-leases", "retry-policy"]),
        ("device-inventory", "Device Management", ["device-registration", "authorization-state"]),
        ("platform-events", "Platform Integration", ["service-registry", "event-bus"]),
        ("communication-center", "Communication Center", ["notifications", "read-state"]),
        ("knowledge-center", "Knowledge Center", ["document-index", "source-search"]),
        ("file-storage", "File Management", ["safe-file-inventory", "metadata-hashing"]),
        ("application-inventory", "Application Management", ["application-registry"])
    ]
    for service_id, display_name, capabilities in services:
        events.register_service(service_id, display_name, "0.3.0", capabilities)

OPENAI_BASE_URL = "https://api.openai.com/v1"

def require_gateway_token(authorization: str | None) -> None:
    expected = os.getenv("JROCAI_GATEWAY_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Gateway authentication is not configured.")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid gateway access token.")

def cloud_spending_enabled() -> bool:
    allow_paid = os.getenv("JROCAI_ALLOW_PAID_CLOUD", "false").strip().lower() == "true"
    try:
        spending_limit = float(os.getenv("JROCAI_MONTHLY_SPENDING_LIMIT_USD", "0"))
    except ValueError:
        spending_limit = 0
    return allow_paid and spending_limit > 0

def provider_key() -> str:
    if not cloud_spending_enabled():
        raise HTTPException(status_code=403, detail="Cloud model execution is blocked by the zero-dollar spending gate.")
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise HTTPException(status_code=503, detail="OpenAI provider key is not configured in the Env Agent.")
    return key

class ChatRequest(BaseModel):
    model: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=20000)
    agent: Literal["assistant", "jbot"] = "assistant"

@app.get("/health")
def health():
    return {"status": "ok", "service": "jrocai-env-agent", "provider_configured": bool(os.getenv("OPENAI_API_KEY")), "cloud_execution_enabled": cloud_spending_enabled()}

@app.get("/v1/environment/status")
def environment_status(authorization: str | None = Header(default=None)):
    require_gateway_token(authorization)
    names = ("OPENAI_API_KEY", "JROCAI_GATEWAY_TOKEN", "JROCAI_ALLOW_PAID_CLOUD", "JROCAI_MONTHLY_SPENDING_LIMIT_USD", "JROCAI_PLATFORM_DATABASE", "JROCAI_FILE_ROOT")
    return {
        "service": "J-ROC AI Environment Agent",
        "secret_values_returned": False,
        "variables": [{"name": name, "configured": bool(os.getenv(name))} for name in names],
        "cloud_execution_enabled": cloud_spending_enabled(),
        "monthly_spending_limit_usd": float(os.getenv("JROCAI_MONTHLY_SPENDING_LIMIT_USD", "0") or "0") if os.getenv("JROCAI_MONTHLY_SPENDING_LIMIT_USD", "0").replace(".", "", 1).isdigit() else 0,
        "policy": "Paid cloud execution requires an explicit enable flag and a positive spending limit."
    }

@app.get("/v1/models")
async def models(authorization: str | None = Header(default=None)):
    require_gateway_token(authorization)
    headers = {"Authorization": f"Bearer {provider_key()}"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{OPENAI_BASE_URL}/models", headers=headers)
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail="Model catalog request failed at provider.")
    data = response.json().get("data", [])
    return {"data": [{"id": item.get("id")} for item in data if item.get("id")]}

@app.post("/v1/chat")
async def chat(payload: ChatRequest, authorization: str | None = Header(default=None)):
    require_gateway_token(authorization)
    if payload.agent == "jbot":
        instructions = ("You are J-Bot, J-ROC AI device troubleshooting and repair intelligence. "
            "Ask for device model and symptoms when missing. Provide safe, stepwise diagnostics. "
            "Never claim to unlock, bypass security, or perform actions you cannot verify. "
            "Warn before data-erasing steps and recommend a backup.")
    else:
        instructions = "You are J-ROC AI Assistant, a precise, helpful personal AI assistant."
    body = {"model": payload.model, "instructions": instructions, "input": payload.message, "store": False}
    headers = {"Authorization": f"Bearer {provider_key()}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(f"{OPENAI_BASE_URL}/responses", headers=headers, json=body)
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail="AI provider request failed. Check Env Agent logs.")
    result = response.json()
    text = result.get("output_text", "")
    if not text:
        chunks = []
        for item in result.get("output", []):
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    chunks.append(part.get("text", ""))
        text = "\n".join(filter(None, chunks))
    return {"reply": text or "No text response was returned.", "model": payload.model}
