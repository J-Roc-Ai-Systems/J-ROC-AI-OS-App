"""J-ROC AI Brain control plane. Plans work without pretending a model is connected."""
from pydantic import BaseModel, Field
from .database import db
from .models import utc_now
from .security import audit

class BrainPlanRequest(BaseModel):
    objective: str = Field(min_length=5,max_length=4000)
    preferred_execution: str = Field(default="local",pattern="^(local|cloud|automatic)$")
    allow_paid_execution: bool = False

class BrainService:
    def status(self):
        return {"brain":"control_plane_available","reasoning_model":"not_connected","memory":"local_knowledge_index","cloud_execution_enabled":False,"spending_limit":0}
    def plan(self, request: BrainPlanRequest):
        if request.preferred_execution == "cloud" or request.allow_paid_execution:
            # No user request can override the server-side zero-dollar gate.
            audit("brain.cloud_request.blocked","brain","model-router","cloud execution is disabled by default")
        steps=[
            {"step":1,"name":"Validate objective","state":"planned"},
            {"step":2,"name":"Retrieve permitted project knowledge","state":"planned"},
            {"step":3,"name":"Identify required capabilities and approvals","state":"planned"},
            {"step":4,"name":"Create bounded worker jobs","state":"requires_approval"},
            {"step":5,"name":"Collect results and produce a traceable summary","state":"planned"}
        ]
        plan={"plan_id":__import__("uuid").uuid4().hex,"objective":request.objective,"execution_policy":"local_only","cloud_execution":"blocked","steps":steps,"created_at":utc_now()}
        audit("brain.plan.create","plan",plan["plan_id"])
        return plan
brain=BrainService()
