"""Source Agent security and route contract tests."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backend"/"env-agent"))
from fastapi import HTTPException
from platform_core.source_agent import validate_repository,validate_source_path,source_agent_status

class SourceAgentTests(unittest.TestCase):
 def test_accepts_valid_repository(self):
  self.assertEqual(("owner","repo"),validate_repository("owner","repo"))
 def test_rejects_repository_path_injection(self):
  with self.assertRaises(HTTPException):validate_repository("owner","..")
 def test_normalizes_windows_file_paths(self):
  self.assertEqual("src/main.py",validate_source_path(r"src\main.py"))
 def test_rejects_parent_directory_traversal(self):
  with self.assertRaises(HTTPException):validate_source_path("src/../../secrets.env")
 def test_source_agent_is_read_only(self):
  status=source_agent_status()
  self.assertEqual("read_only",status["scope"])
  self.assertFalse(status["writes_enabled"])
  self.assertFalse(status["secret_values_returned"])
if __name__=="__main__":unittest.main()
