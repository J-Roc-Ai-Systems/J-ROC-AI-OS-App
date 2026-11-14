"""Checks that the public application mounts the shared Wave Three to Five routes."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"/"env-agent"))
from app import app

class WaveApiMountTests(unittest.TestCase):
    def test_wave_catalog_and_domain_routes_are_mounted(self):
        paths=set(app.openapi()["paths"].keys())
        self.assertIn("/platform/v1/waves",paths)
        self.assertIn("/platform/v1/domain/catalog",paths)
        self.assertIn("/platform/v1/domain/{domain}/records",paths)
        self.assertIn("/platform/v1/domain/{domain}/records/{record_id}/state",paths)
        self.assertIn("/platform/v1/waves/6-10",paths)
        self.assertIn("/platform/v1/wave-resources/catalog",paths)
        self.assertIn("/platform/v1/agent-jobs/{job_id}/dispatch",paths)
        self.assertIn("/platform/v1/agent-jobs/{job_id}",paths)
        self.assertIn("/platform/v1/source-agent/status",paths)
        self.assertIn("/platform/v1/source-agent/repositories/{owner}/{repo}/tree",paths)
        self.assertIn("/platform/v1/source-agent/repositories/{owner}/{repo}/files",paths)
        self.assertIn("/platform/v1/waves/11-15",paths)
        self.assertIn("/platform/v1/wave-eleven-fifteen/catalog",paths)
        self.assertIn("/platform/v1/wave-eleven-fifteen/records/{collection}",paths)
        self.assertIn("/platform/v1/wave-eleven-fifteen/records/{collection}/{record_id}/state",paths)

if __name__=="__main__": unittest.main()
