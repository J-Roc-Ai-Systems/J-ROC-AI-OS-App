import unittest
from source_agent.github_client import GitHubReadClient

class GitHubClientTests(unittest.TestCase):
    def test_parse_repository(self):
        self.assertEqual(GitHubReadClient.parse_repository("owner/project"), ("owner", "project"))
    def test_rejects_invalid_repository(self):
        with self.assertRaises(ValueError):
            GitHubReadClient.parse_repository("project-only")

if __name__ == "__main__":
    unittest.main()
