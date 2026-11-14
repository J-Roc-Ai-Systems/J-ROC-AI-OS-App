"""Regression tests for Wave Eleven through Fifteen service foundations."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "env-agent"))
import platform_core.wave1115 as wave
import platform_core.security as security
from platform_core.database import PlatformDatabase
from platform_core.wave1115 import RecordCreate, RecordTransition


class WaveElevenFifteenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_db = wave.db
        self.previous_security_db = security.db
        wave.db = PlatformDatabase(Path(self.temp.name) / "wave1115.sqlite3")
        security.db = wave.db
        wave.db.connect()

    def tearDown(self):
        wave.db = self.previous_db
        security.db = self.previous_security_db
        self.temp.cleanup()

    def test_catalog_covers_fifty_batches_and_collections(self):
        catalog = wave.list_waves_eleven_to_fifteen()
        self.assertEqual((5, 50, 101, 150), (catalog["wave_count"], catalog["batch_count"], catalog["first_batch"], catalog["last_batch"]))
        self.assertEqual(50, wave.collection_catalog()["count"])
        self.assertEqual(set(wave.COLLECTIONS), set(wave.REQUIRED))

    def test_creates_and_reads_validated_knowledge_record(self):
        record = wave.create_record("knowledge_entities", RecordCreate(title="J-ROC AI platform entity", data={"entity_type": "platform", "canonical_name": "J-ROC AI"}))
        self.assertEqual("knowledge_entities", record["collection"])
        fetched = wave.get_record("knowledge_entities", record["record_id"])
        self.assertEqual("J-ROC AI", fetched["data"]["canonical_name"])

    def test_missing_required_fields_are_rejected(self):
        with self.assertRaises(Exception):
            wave.create_record("invoices", RecordCreate(title="Incomplete invoice", data={"invoice_number": "INV-1"}))

    def test_secrets_are_removed_before_persistence(self):
        record = wave.create_record("notes", RecordCreate(title="Safe note", data={"title": "Operational note", "content": "No secrets", "api_key": "never-store-this"}))
        self.assertNotIn("api_key", record["data"])
        self.assertNotIn("never-store-this", str(record))

    def test_automation_steps_are_allowlisted(self):
        with self.assertRaises(Exception):
            wave.create_record("automation_recipes", RecordCreate(title="Unsafe automation", data={"trigger": "manual", "steps": [{"type": "shell", "command": "no"}]}))

    def test_media_rights_must_be_classified(self):
        with self.assertRaises(Exception):
            wave.create_record("media_assets", RecordCreate(title="Unclassified media", data={"asset_reference": "asset-1", "media_type": "audio", "rights_status": "unknown"}))

    def test_risk_scores_are_bounded(self):
        with self.assertRaises(Exception):
            wave.create_record("governance_risks", RecordCreate(title="Out of range risk", data={"risk_title": "Risk", "likelihood": 8, "impact": 2, "owner": "team"}))

    def test_financial_boolean_amount_is_rejected(self):
        with self.assertRaises(Exception):
            wave.create_record("expense_records", RecordCreate(title="Invalid expense", data={"amount": True, "currency": "USD", "category": "travel", "occurred_at": "2026-11-13"}))

    def test_approval_pending_record_cannot_be_activated(self):
        record = wave.create_record("configuration_changes", RecordCreate(title="Production configuration change", state="awaiting_approval", data={"system_reference": "gateway", "change_summary": "Rotate configuration", "requested_by": "operator"}))
        with self.assertRaises(Exception):
            wave.transition_record("configuration_changes", record["record_id"], RecordTransition(state="active", reason="Attempt without approval"))
        approved = wave.transition_record("configuration_changes", record["record_id"], RecordTransition(state="approved", reason="Reviewed and approved"))
        self.assertEqual("approved", approved["state"])

    def test_terminal_records_cannot_be_reopened(self):
        record = wave.create_record("notes", RecordCreate(title="Closed note", data={"title": "Close", "content": "Record"}))
        wave.transition_record("notes", record["record_id"], RecordTransition(state="completed", reason="Work completed"))
        with self.assertRaises(Exception):
            wave.transition_record("notes", record["record_id"], RecordTransition(state="active", reason="Reopen attempt"))


if __name__ == "__main__":
    unittest.main()
