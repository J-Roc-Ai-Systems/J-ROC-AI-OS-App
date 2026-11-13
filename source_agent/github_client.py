from __future__ import annotations
import json
import os
import urllib.error
import urllib.parse
import urllib.request

class GitHubApiError(RuntimeError):
    pass

class GitHubReadClient:
    """Read-only GitHub REST adapter. Credentials are server-side environment secrets."""
    API_ROOT = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.token = token if token is not None else os.environ.get("JROC_GITHUB_TOKEN", "")

    @staticmethod
    def parse_repository(repository: str) -> tuple[str, str]:
        parts = repository.strip().strip("/").split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError("Repository must use owner/name format")
        return parts[0], parts[1]

    def get_json(self, path: str) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "J-ROC-AI-Source-Agent",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.API_ROOT + path, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                value = json.loads(response.read().decode("utf-8"))
                if not isinstance(value, dict):
                    raise GitHubApiError("GitHub returned an unexpected response")
                return value
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise GitHubApiError("Repository or resource was not found or is not accessible") from exc
            if exc.code == 401:
                raise GitHubApiError("GitHub token is invalid or expired") from exc
            if exc.code == 403:
                raise GitHubApiError("GitHub denied access or rate limit was reached") from exc
            raise GitHubApiError(f"GitHub API request failed with HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise GitHubApiError("Could not connect to GitHub") from exc

    def inspect_repository(self, repository: str) -> dict:
        owner, name = self.parse_repository(repository)
        data = self.get_json(f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}")
        return {
            "full_name": data.get("full_name"),
            "private": data.get("private"),
            "default_branch": data.get("default_branch"),
            "html_url": data.get("html_url"),
            "description": data.get("description"),
            "archived": data.get("archived"),
        }

    def read_file(self, repository: str, path: str, ref: str | None = None) -> dict:
        owner, name = self.parse_repository(repository)
        encoded_path = urllib.parse.quote(path.lstrip("/"), safe="/")
        query = f"?ref={urllib.parse.quote(ref)}" if ref else ""
        data = self.get_json(f"/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(name)}/contents/{encoded_path}{query}")
        if data.get("type") != "file":
            raise GitHubApiError("Requested path is not a file")
        return {"path": data.get("path"), "sha": data.get("sha"), "html_url": data.get("html_url"), "content": data.get("content"), "encoding": data.get("encoding")}
