"""Validated domain models for Wave Two platform services."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ConfigDict

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class WorkerState(str, Enum):
    REGISTERED = "registered"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DISABLED = "disabled"

class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkerRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    worker_id: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str = Field(min_length=2, max_length=120)
    worker_type: str = Field(min_length=2, max_length=80)
    capabilities: list[str] = Field(default_factory=list, max_length=40)
    max_concurrent_jobs: int = Field(default=1, ge=1, le=8)

class JobSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_type: str = Field(min_length=2, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    required_capability: str | None = Field(default=None, max_length=80)
    max_attempts: int = Field(default=3, ge=1, le=10)

class IntegrationRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    integration_id: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str = Field(min_length=2, max_length=120)
    integration_type: str = Field(min_length=2, max_length=80)
    provider: str = Field(min_length=2, max_length=120)
    capabilities: list[str] = Field(default_factory=list, max_length=40)
    secret_reference: str | None = Field(default=None, max_length=240)

class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_name: str = Field(min_length=2, max_length=120)
    project_type: str = Field(min_length=2, max_length=60)
    target_platforms: list[str] = Field(default_factory=list, max_length=10)
    description: str = Field(default="", max_length=4000)

class DeviceRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=2, max_length=120, pattern=r"^[a-zA-Z0-9._:-]+$")
    display_name: str = Field(min_length=2, max_length=120)
    device_type: str = Field(min_length=2, max_length=60)
    connection_type: str = Field(min_length=2, max_length=40)
    capabilities: list[str] = Field(default_factory=list, max_length=40)

class ApplicationRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_id: str = Field(min_length=2, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str = Field(min_length=2, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    platform: str = Field(min_length=2, max_length=40)
    package_reference: str | None = Field(default=None, max_length=500)
