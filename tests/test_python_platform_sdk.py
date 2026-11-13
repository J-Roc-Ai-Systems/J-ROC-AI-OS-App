"""Unit tests for the Python platform SDK without network access."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"sdk"/"python"))
from jrocai_platform import JrocAiPlatformClient, PlatformApiError

class PythonSdkTests(unittest.TestCase):
    def test_requires_https_or_loopback(self):
        with self.assertRaises(ValueError): JrocAiPlatformClient("http://example.com","token")
        self.assertIsNotNone(JrocAiPlatformClient("http://127.0.0.1:8787","token"))
    def test_requires_token(self):
        with self.assertRaises(ValueError): JrocAiPlatformClient("https://localhost","")
    def test_rejects_path_traversal(self):
        client=JrocAiPlatformClient("https://example.com","token")
        with self.assertRaises(ValueError): client.request("GET","/platform/../admin")
    def test_api_error_preserves_status(self):
        error=PlatformApiError(403,"blocked")
        self.assertEqual(403,error.status)

if __name__=="__main__": unittest.main()
