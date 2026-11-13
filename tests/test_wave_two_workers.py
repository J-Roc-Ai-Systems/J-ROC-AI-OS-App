"""Focused regression tests for Wave Two migrations and worker lifecycle."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "env-agent"))

from platform_core.database import PlatformDatabase
from platform_core.models import WorkerRegistration, JobSubmission
from platform_core.workers import WorkerService

class WaveTwoWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = PlatformDatabase(Path(self.temp.name) / "platform.sqlite3")
        self.database.connect()
        import platform_core.workers as worker_module
        self.previous_db = worker_module.db
        worker_module.db = self.database
        self.service = WorkerService()

    def tearDown(self):
        import platform_core.workers as worker_module
        worker_module.db = self.previous_db
        self.temp.cleanup()

    def test_migrations_are_recorded_and_additive(self):
        versions = self.database.many("SELECT version FROM schema_migrations ORDER BY version")
        self.assertEqual([1], [row["version"] for row in versions])
        columns = {row["name"] for row in self.database.many("PRAGMA table_info(jobs)")}
        self.assertTrue({"lease_expires_at", "max_attempts", "cancel_requested"}.issubset(columns))

    def test_worker_secret_is_one_time_and_required(self):
        registered = self.service.register(WorkerRegistration(worker_id="test-worker",display_name="Test Worker",worker_type="test",capabilities=["unit-test"]))
        token = registered["worker_token"]
        self.assertTrue(self.service.authenticate("test-worker", token))
        self.assertFalse(self.service.authenticate("test-worker", "wrong-token"))
        self.assertNotIn("token_hash", self.service.get("test-worker"))
        self.assertNotIn("worker_token", self.service.get("test-worker"))

    def test_claim_requires_capability_and_lease(self):
        self.service.register(WorkerRegistration(worker_id="worker-a",display_name="Worker A",worker_type="test",capabilities=["compile"]))
        self.service.submit(JobSubmission(job_type="test.job",payload={"safe":True},required_capability="compile"))
        claimed = self.service.claim("worker-a", 45)
        self.assertEqual("running", claimed["state"])
        self.assertEqual("worker-a", claimed["assigned_worker"])
        self.assertIsNotNone(claimed["lease_expires_at"])
        self.assertEqual(1, claimed["attempts"])

    def test_cancel_and_retry_are_bounded(self):
        self.service.register(WorkerRegistration(worker_id="worker-b",display_name="Worker B",worker_type="test",capabilities=["test"]))
        job = self.service.submit(JobSubmission(job_type="test.job",max_attempts=2))
        cancelled = self.service.cancel(job["job_id"])
        self.assertEqual("cancelled", cancelled["state"])
        retried = self.service.retry(job["job_id"])
        self.assertEqual("queued", retried["state"])

    def test_invalid_worker_credential_is_rejected(self):
        self.service.register(WorkerRegistration(worker_id="worker-c",display_name="Worker C",worker_type="test"))
        self.assertFalse(self.service.authenticate("worker-c", None))
        self.assertFalse(self.service.authenticate("worker-c", "invalid"))

if __name__ == "__main__":
    unittest.main()
