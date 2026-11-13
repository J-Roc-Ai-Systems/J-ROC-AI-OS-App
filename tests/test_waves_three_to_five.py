"""Regression tests for shared Wave Three to Five governance foundations."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"/"env-agent"))
import platform_core.wave345 as module
import platform_core.domain_records as domains
from platform_core.database import PlatformDatabase
from platform_core.wave345 import WorkflowCreate, WorkflowDecision, PolicyCheck

class WaveThreeFiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old_db=module.db
        self.old_domain_db=domains.db
        module.db=PlatformDatabase(Path(self.temp.name)/"test.sqlite3")
        domains.db=module.db
        module.db.connect()
    def tearDown(self):
        module.db=self.old_db
        domains.db=self.old_domain_db
        self.temp.cleanup()
    def test_catalogue_has_thirty_batches(self):
        self.assertEqual(30,sum(len(w["batches"]) for w in module.WAVES))
        self.assertEqual(21,module.WAVES[0]["batches"][0][0])
        self.assertEqual(50,module.WAVES[-1]["batches"][-1][0])
    def test_workflow_requires_approval_and_decision(self):
        item=WorkflowCreate(workflow_type="repair.plan",title="Repair plan",objective="Prepare a safe repair plan",batch=34,steps=["verify device","collect evidence"])
        result=module.create_workflow(item)
        self.assertEqual("awaiting_approval",result["state"])
        approved=module.decide_workflow(result["workflow_id"],WorkflowDecision(decision="approve",reason="Owner approved the plan"))
        self.assertEqual("approved_queued",approved["state"])
        self.assertTrue(approved["requires_approval"])
    def test_rejects_invalid_batch(self):
        with self.assertRaises(Exception):
            module.create_workflow(WorkflowCreate(workflow_type="test.plan",title="Invalid batch",objective="This batch is outside supported waves",batch=20))
    def test_zero_dollar_gate_denies_paid_execution(self):
        os.environ.pop("JROCAI_ALLOW_PAID_CLOUD",None)
        os.environ.pop("JROCAI_MONTHLY_SPENDING_LIMIT_USD",None)
        result=module.evaluate_policy(PolicyCheck(action="model.invoke",estimated_cost_usd=0.01))
        self.assertEqual("deny",result["outcome"])
        self.assertFalse(result["execution_performed"])
    def test_wave_four_and_five_domain_records_persist_and_redact_credentials(self):
        item=domains.DomainRecordCreate(title="Galaxy diagnostic",data={"model":"Galaxy S24","api_key":"must-not-persist","symptoms":["no charge"]})
        saved=domains.create_record("diagnostics",item)
        self.assertEqual(33,saved["batch"])
        self.assertNotIn("api_key",saved["data"])
        self.assertEqual(saved["record_id"],domains.get_record("diagnostics",saved["record_id"])["record_id"])
    def test_domain_catalog_covers_all_twenty_batches(self):
        self.assertEqual(20,len(domains.domain_catalog()["domains"]))
    def test_destructive_action_requires_approval(self):
        result=module.evaluate_policy(PolicyCheck(action="erase_device_data",resource_type="device",resource_id="device-1",destructive=True))
        self.assertEqual("requires_approval",result["outcome"])

if __name__=="__main__": unittest.main()
