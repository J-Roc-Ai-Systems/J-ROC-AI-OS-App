"""Regression tests for Wave Six through Ten."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"/"env-agent"))
import platform_core.wave610 as m
import platform_core.security as security
from platform_core.database import PlatformDatabase
from platform_core.wave610 import AgentRegistration,AgentJobCreate,JobDecision
class WaveSixTenTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.old=m.db;self.oldsec=security.db
  m.db=PlatformDatabase(Path(self.t.name)/"test.sqlite3");security.db=m.db;m.db.connect()
 def tearDown(self):
  m.db=self.old;security.db=self.oldsec;self.t.cleanup()
 def test_fifty_batches(self):self.assertEqual((50,51,100),(m.list_waves_six_to_ten()["batch_count"],min(m.BATCHES),max(m.BATCHES)))
 def test_approval_gated_agent_job(self):
  m.register_agent(AgentRegistration(agent_id="source-agent",display_name="Source Agent",capabilities=["repository.inspect"]))
  job=m.create_agent_job(AgentJobCreate(job_type="repository.review",title="Review repository",objective="Inspect repository structure and missing modules",batch=53,agent_id="source-agent",repository="owner/repository",file_scope=["backend","tests"]))
  self.assertEqual("awaiting_approval",job["state"])
  result=m.decide_agent_job(job["job_id"],JobDecision(decision="approve",reason="Approved for inspection"))
  self.assertEqual("approved_queued",result["state"])
 def test_unregistered_agent_denied(self):
  with self.assertRaises(Exception):m.create_agent_job(AgentJobCreate(job_type="docs.review",title="Review docs",objective="Review platform documentation",batch=57,agent_id="missing"))
 def test_unsafe_path_denied(self):
  m.register_agent(AgentRegistration(agent_id="test-agent",display_name="Test Agent"))
  with self.assertRaises(Exception):m.create_agent_job(AgentJobCreate(job_type="test.run",title="Run tests",objective="Run the repository test suite",batch=56,agent_id="test-agent",file_scope=["../../secrets.env"]))
 def test_sensitive_operation_denied(self):
  m.register_agent(AgentRegistration(agent_id="repair-agent",display_name="Repair Agent"))
  with self.assertRaises(Exception):m.create_agent_job(AgentJobCreate(job_type="device_unlock",title="Unlock device",objective="Unlock device security",batch=72,agent_id="repair-agent"))
 def test_decision_cannot_be_repeated(self):
  m.register_agent(AgentRegistration(agent_id="docs-agent",display_name="Docs Agent"))
  j=m.create_agent_job(AgentJobCreate(job_type="docs.review",title="Review docs",objective="Review technical documentation",batch=57,agent_id="docs-agent"))
  m.decide_agent_job(j["job_id"],JobDecision(decision="reject",reason="Needs more evidence"))
  with self.assertRaises(Exception):m.decide_agent_job(j["job_id"],JobDecision(decision="approve",reason="Late approval"))
if __name__=="__main__":unittest.main()
