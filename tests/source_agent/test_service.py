import tempfile
import unittest
from pathlib import Path
from source_agent.service import AgentStore

class AgentStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=AgentStore(str(Path(self.temp.name)/"agent.sqlite3"))
    def tearDown(self):
        self.temp.cleanup()
    def test_inspection_task_is_queued(self):
        task=self.store.create_task({"agent_id":"source-agent","task_type":"repository.inspect","repository":"J-Roc-Ai-Systems/J-ROC-AI-OS-App","description":"Inspect project"})
        self.assertEqual(task["status"],"queued")
        self.assertEqual(task["requires_approval"],0)
    def test_source_write_requires_approval(self):
        task=self.store.create_task({"agent_id":"source-agent","task_type":"source.write","repository":"org/repo","description":"Propose source change"})
        self.assertEqual(task["status"],"pending_approval")
        self.assertEqual(task["requires_approval"],1)
    def test_approval_updates_task(self):
        task=self.store.create_task({"agent_id":"source-agent","task_type":"build.execute","repository":"org/repo","description":"Run build"})
        updated=self.store.approve(task["task_id"],True,"chairman")
        self.assertEqual(updated["status"],"queued")
        self.assertEqual(updated["approved_by"],"chairman")
    def test_unknown_agent_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create_task({"agent_id":"unknown","task_type":"repository.inspect","repository":"org/repo","description":"inspect"})

if __name__=="__main__":
    unittest.main()
