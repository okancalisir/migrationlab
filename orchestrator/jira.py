"""Read-only Jira Cloud client using the Python standard library."""

import base64
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward credentials to a redirect target.
        return None


def load_settings(root: Path) -> dict[str, str]:
    settings = {}
    env_file = root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator:
                raise ValueError("Invalid .env line; expected KEY=value.")
            settings[key.strip()] = value.strip().strip("\"'")
    for key in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_CLOUD_ID"):
        if key in os.environ:
            settings[key] = os.environ[key].strip()
    return settings


class JiraClient:
    def __init__(self, settings: dict[str, str]):
        for key in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
            if not settings.get(key):
                raise ValueError(f"Set {key} in the local .env file or environment.")
        site = settings["JIRA_BASE_URL"].rstrip("/")
        parsed = urlsplit(site)
        if (parsed.scheme != "https" or not parsed.hostname
                or not parsed.hostname.endswith(".atlassian.net")
                or parsed.username or parsed.password or parsed.port
                or parsed.path or parsed.query or parsed.fragment):
            raise ValueError("JIRA_BASE_URL must be https://your-site.atlassian.net")
        cloud_id = settings.get("JIRA_CLOUD_ID", "")
        if cloud_id and not re.fullmatch(r"[A-Za-z0-9-]+", cloud_id):
            raise ValueError("Invalid JIRA_CLOUD_ID.")
        self.base = f"https://api.atlassian.com/ex/jira/{cloud_id}" if cloud_id else site
        credentials = f"{settings['JIRA_EMAIL']}:{settings['JIRA_API_TOKEN']}"
        self._authorization = "Basic " + base64.b64encode(credentials.encode()).decode()

    def get(self, path: str) -> dict:
        if not path.startswith("/rest/api/3/"):
            raise ValueError("Only Jira REST v3 paths are supported.")
        request = Request(self.base + path, headers={
            "Authorization": self._authorization,
            "Accept": "application/json",
        })
        try:
            with build_opener(NoRedirect()).open(request, timeout=30) as response:
                result = json.load(response)
        except HTTPError as exc:
            messages = {
                401: "Authentication failed; check email, token and scoped-token cloud ID.",
                403: "Access denied; check account permissions and token scopes.",
                404: "Resource not found or not visible to this account.",
                429: "Jira rate limit reached; retry later.",
            }
            raise ValueError(f"Jira HTTP {exc.code}: {messages.get(exc.code, 'Request failed.')} ") from None
        except URLError:
            raise ValueError("Could not connect to Jira; check network access.") from None
        except (TimeoutError, json.JSONDecodeError):
            raise ValueError("Jira timed out or returned invalid JSON.") from None
        if not isinstance(result, dict):
            raise ValueError("Unexpected Jira response format.")
        return result

    def check_connection(self) -> None:
        if not self.get("/rest/api/3/myself").get("accountId"):
            raise ValueError("Jira did not return an authenticated account.")

    def get_issue(self, issue: str) -> dict:
        if not re.fullmatch(r"[A-Z][A-Z0-9]*-[0-9]+", issue):
            raise ValueError("Expected an issue ID such as MIG-1.")
        return self.get(f"/rest/api/3/issue/{issue}?fields=summary,description,attachment,status")
