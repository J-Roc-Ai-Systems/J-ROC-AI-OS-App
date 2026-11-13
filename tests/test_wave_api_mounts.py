"""Checks that the public application mounts the shared Wave Three to Five routes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"/"env-agent"))
from app import app

class WaveApiMountTests:
    def test_wave_catalog_and_domain_routes_are_mounted(self):
        paths={route.path for route in app.routes}
        self.assertIn("/platform/v1/waves",paths)
        self.assertIn("/platform/v1/domain/catalog",paths)
        self.assertIn("/platform/v1/domain/{domain}/records",paths)
        self.assertIn("/platform/v1/domain/{domain}/records/{record_id}/state",paths)
