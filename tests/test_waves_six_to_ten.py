"""Regression tests for Wave Six through Ten."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"/"env-agent"))
import platform_core.wave610 as m
import platform_core.security as security
import platform_core.workers as worker_module
from platform_core.database import PlatformDatabase
from platform_core.wave610 import AgentRegistration,AgentJobCreate,JobDecision,ResourceCreate
class WaveSixTenTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.old=m.db;self.oldsec=security.db;self.oldworker=worker_module.db
  m.db=PlatformDatabase(Path(self.t.name)/"test.sqlite3");security.db=m.db;worker_module.db=m.db;m.db.connect()
 def tearDown(self):
  m.db=self.old;security.db=self.oldsec;worker_module.db=self.oldworker;self.t.cleanup()
 def test_fifty_batches(self):self.assertEqual((50,51,100),(m.list_waves_six_to_ten()["batch_count"],min(m.BATCHES),max(m.BATCHES)))
 def test_approval_gated_agent_job(self):
  m.register_agent(AgentRegistration(agent_id="source-agent",display_name="Source Agent",capabilities=["repository.inspect"]))
  job=m.create_agent_job(AgentJobCreate(job_type="repository.review",title="Review repository",objective="Inspect repository structure and missing modules",batch=53,agent_id="source-agent",repository="owner/repository",file_scope=["backend","tests"]))
  self.assertEqual("awaiting_approval",job["state"])
  result=m.decide_agent_job(job["job_id"],JobDecision(decision="approve",reason="Approved for inspection"))
  self.assertEqual("approved_queued",result["state"])
 def test_unregistered_agent_denied(self):
  with self.assertRaises(Exception):m.create_agent_job(AgentJobCreate(job_type="documentation.review",title="Review docs",objective="Review platform documentation",batch=57,agent_id="missing"))
 def test_unsafe_path_denied(self):
  m.register_agent(AgentRegistration(agent_id="test-agent",display_name="Test Agent"))
  with self.assertRaises(Exception):m.create_agent_job(AgentJobCreate(job_type="test.run",title="Run tests",objective="Run the repository test suite",batch=56,agent_id="test-agent",file_scope=["../../secrets.env"]))
 def test_sensitive_operation_denied(self):
  m.register_agent(AgentRegistration(agent_id="repair-agent",display_name="Repair Agent"))
  with self.assertRaises(Exception):m.create_agent_job(AgentJobCreate(job_type="device_unlock",title="Unlock device",objective="Unlock device security",batch=72,agent_id="repair-agent"))
 def test_decision_cannot_be_repeated(self):
  m.register_agent(AgentRegistration(agent_id="docs-agent",display_name="Docs Agent"))
  j=m.create_agent_job(AgentJobCreate(job_type="documentation.review",title="Review docs",objective="Review technical documentation",batch=57,agent_id="docs-agent"))
  m.decide_agent_job(j["job_id"],JobDecision(decision="reject",reason="Needs more evidence"))
  with self.assertRaises(Exception):m.decide_agent_job(j["job_id"],JobDecision(decision="approve",reason="Late approval"))

 def test_every_wave_resource_has_a_typed_contract(self):
  self.assertEqual(set(m.RESOURCE_TYPES),set(m.RESOURCE_REQUIRED))
 def test_workflow_steps_are_allowlisted(self):
  with self.assertRaises(Exception):m.create_wave_resource("workflow_definitions",ResourceCreate(title="Unsafe workflow",data={"steps":[{"type":"shell","command":"not allowed"}]}))
 def test_domain_resource_contract_validation(self):
  with self.assertRaises(Exception):
   m.create_wave_resource("source_reviews",ResourceCreate(title="Missing repository",data={"notes":"not enough"}))
  resource=m.create_wave_resource("source_reviews",ResourceCreate(title="Inspect repository",data={"repository":"owner/repo"}))
  self.assertEqual("source_reviews",resource["resource_type"])
 def test_device_enrollment_requires_owner_confirmation(self):
  with self.assertRaises(Exception):
   m.create_wave_resource("device_enrollments",ResourceCreate(title="Enroll phone",data={"device_id":"phone-1","owner_confirmation":False}))
 def test_local_model_registry_rejects_remote_runtime(self):
  with self.assertRaises(Exception):
   m.create_wave_resource("local_models",ResourceCreate(title="Remote model",data={"model_id":"remote-model","runtime":"hosted"}))
 def test_bootstrap_registers_permanent_source_agent(self):
  result=m.ensure_default_agents()
  self.assertEqual(14,result["registered"])
  self.assertIsNotNone(m.db.one("SELECT agent_id FROM platform_agent_registry WHERE agent_id='source-agent'"))
 def test_approved_job_dispatches_to_authenticated_worker_queue(self):
  from platform_core.models import WorkerRegistration
  m.register_agent(AgentRegistration(agent_id="source-agent",display_name="Source Agent",capabilities=["repository.inspect"]))
  registered=worker_module.workers.register(WorkerRegistration(worker_id="source-runner",display_name="Source Runner",worker_type="source",capabilities=["agent:source-agent"]))
  job=m.create_agent_job(AgentJobCreate(job_type="repository.review",title="Review repository",objective="Inspect repository structure and missing modules",batch=53,agent_id="source-agent"))
  m.decide_agent_job(job["job_id"],JobDecision(decision="approve",reason="Approved source review"))
  queued=m.dispatch_approved_agent_job(job["job_id"])
  self.assertEqual("queued",queued["worker_queue_state"])
  self.assertEqual("dispatched",m.get_agent_job(job["job_id"])["state"])
  claimed=worker_module.workers.claim("source-runner",45)
  self.assertEqual(queued["worker_job_id"],claimed["job_id"])
  completed=worker_module.workers.finish(claimed["job_id"],"source-runner",{"status":"reviewed","files_checked":2})
  self.assertEqual("completed",completed["state"])
  self.assertEqual(queued["worker_job_id"],m.db.one("SELECT worker_job_id FROM platform_agent_jobs WHERE job_id=?",(job["job_id"],))["worker_job_id"])
 def test_environment_readiness_never_returns_secret_values(self):
  result=m.environment_readiness()
  self.assertNotIn("OPENAI_API_KEY_VALUE",str(result))
  self.assertFalse(result["secret_values_returned"])

if __name__=="__main__":unittest.main()
