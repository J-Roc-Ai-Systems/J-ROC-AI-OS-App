"""J-ROC AI Env Agent: server-side secret boundary and authenticated OpenAI gateway.

Provider credentials are read only from process environment. Never return secret values.
"""
import hmac
import os
from typing import Literal

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="J-ROC AI Env Agent", version="0.2.0")

from platform_core.api import router as platform_router, worker_router
from platform_core.identity import router as identity_router, admin_router as identity_admin_router
from platform_core.workflow_engine import router as workflow_router
from platform_core.local_model_router import router as local_model_router
from platform_core.repair_intelligence import router as repair_router
from platform_core.build_factory import router as build_factory_router
from platform_core.secure_storage import router as secure_storage_router
from platform_core.enterprise import router as enterprise_router
from platform_core.release_management import router as release_router
from platform_core.agent_factory import router as agent_factory_router

app.include_router(platform_router)
app.include_router(worker_router)
app.include_router(identity_router)
app.include_router(identity_admin_router)
app.include_router(workflow_router)
app.include_router(local_model_router)
app.include_router(repair_router)
app.include_router(build_factory_router)
app.include_router(secure_storage_router)
app.include_router(enterprise_router)
app.include_router(release_router)
app.include_router(agent_factory_router)


@app.on_event("startup")
def register_wave_two_services():
    from platform_core.events import events
    services = [
        ("application-factory", "Application Factory", ["project-registration", "workspace-preparation"]),
        ("artificial-intelligence-brain", "Artificial Intelligence Brain", ["local-planning", "spending-policy"]),
        ("integration-registry", "Integration Registry", ["connection-registration", "secret-references"]),
        ("production-workers", "Production Worker System", ["worker-registry", "durable-jobs"]),
        ("device-inventory", "Device Management", ["device-registration", "authorization-state"]),
        ("platform-events", "Platform Integration", ["service-registry", "event-bus"]),
        ("communication-center", "Communication Center", ["notifications", "read-state"]),
        ("knowledge-center", "Knowledge Center", ["document-index", "source-search"]),
        ("file-storage", "File Management", ["safe-file-inventory", "metadata-hashing"]),
        ("application-inventory", "Application Management", ["application-registry"]),
        ("account-identity", "Account Identity", ["registration", "sessions", "revocation"]),
        ("workflow-engine", "Workflow Engine", ["definitions", "durable-run-state"]),
        ("local-model-router", "Local Model Router", ["loopback-discovery", "local-inference"]),
        ("repair-intelligence", "Repair Intelligence", ["compatibility-profiles", "diagnostic-sessions"]),
        ("security-governance", "Security Governance", ["audit", "secret-boundary"]),
        ("release-management", "Release Management", ["version-registry", "approval-gates"]),
        ("build-factory", "Build Factory", ["recipe-registry", "approval-gated-build-jobs"]),
        ("encrypted-file-storage", "Encrypted File Storage", ["authenticated-upload", "authenticated-download"]),
        ("enterprise-operations", "Enterprise Operations", ["organizations", "fleet-enrollment", "device-policies"]),
        ("release-channels", "Release Channels", ["release-registry", "approval-and-publish-state"]),
        ("agent-factory", "Agent Factory", ["versioned-definitions", "permission-allowlists"]),
        ("worker-heartbeats", "Worker Heartbeat Service", ["worker-health", "lease-renewal"])
    ]
    for service_id, display_name, capabilities in services:
        events.register_service(service_id, display_name, "0.2.0", capabilities)

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

def local_model_base_url() -> str:
    from urllib.parse import urlparse
    value = os.getenv("JROCAI_LOCAL_MODEL_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
        raise HTTPException(status_code=503, detail="Local model endpoint must be an HTTP loopback address.")
    return value

@app.get("/v1/models")
async def models(authorization: str | None = Header(default=None)):
    require_gateway_token(authorization)
    local_data = []
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            local_response = await client.get(local_model_base_url() + "/api/tags")
        local_response.raise_for_status()
        local_data = [{"id": item.get("name")} for item in local_response.json().get("models", []) if item.get("name")]
    except (httpx.HTTPError, ValueError):
        local_data = []
    if not cloud_spending_enabled():
        return {"data": local_data, "provider": "ollama-local", "cloud_fallback": False}
    headers = {"Authorization": f"Bearer {provider_key()}"}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{OPENAI_BASE_URL}/models", headers=headers)
    if response.is_error:
        raise HTTPException(status_code=response.status_code, detail="Model catalog request failed at provider.")
    cloud_data = [{"id": item.get("id")} for item in response.json().get("data", []) if item.get("id")]
    return {"data": local_data + cloud_data, "local_count": len(local_data), "cloud_count": len(cloud_data)}

@app.post("/v1/chat")
async def chat(payload: ChatRequest, authorization: str | None = Header(default=None)):
    require_gateway_token(authorization)
    if payload.agent == "jbot":
        instructions = (
            "You are J-Bot, J-ROC AI device troubleshooting and repair intelligence. "
            "Ask for device model and symptoms when missing. Provide safe, stepwise diagnostics. "
            "Never claim to unlock, bypass security, or perform actions you cannot verify. "
            "Warn before data-erasing steps and recommend a backup."
        )
    else:
        instructions = "You are J-ROC AI Assistant, a precise, helpful personal AI assistant."
    local_body = {"model": payload.model, "stream": False, "messages": [
        {"role": "system", "content": instructions}, {"role": "user", "content": payload.message}]}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            local_response = await client.post(local_model_base_url() + "/api/chat", json=local_body)
        local_response.raise_for_status()
        local_text = local_response.json().get("message", {}).get("content", "")
        if local_text:
            return {"reply": local_text, "model": payload.model, "provider": "ollama-local", "cloud_fallback": False}
    except (httpx.HTTPError, ValueError):
        pass
    if not cloud_spending_enabled():
        raise HTTPException(status_code=503, detail="Local model is unavailable or does not contain the selected model. Cloud execution remains blocked by the zero-dollar spending gate.")
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
    return {"reply": text or "No text response was returned.", "model": payload.model, "provider": "openai-cloud", "cloud_fallback": True}
