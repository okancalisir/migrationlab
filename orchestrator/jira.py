"""Read-only Jira Cloud client using the Python standard library."""

import base64
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SUPPORTED_SOURCE_EXTENSIONS = {
    ".biz", ".jca", ".md", ".pipeline", ".properties", ".proxy",
    ".service", ".txt", ".wsdl", ".xml", ".xq", ".xquery", ".xqy",
    ".xsd", ".yaml", ".yml",
}
MAX_ATTACHMENT_BYTES = 1_000_000
MAX_TOTAL_ATTACHMENT_BYTES = 3_000_000


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
    for key in (
        "JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_CLOUD_ID",
        "OPENAI_API_KEY", "OPENAI_MODEL",
    ):
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

    def download_attachments(self, attachments: list[dict], destination: Path) -> list[dict]:
        """Download supported text source files and return a safe manifest."""
        destination.mkdir(parents=True, exist_ok=True)
        manifest = []
        total = 0
        for attachment in attachments:
            attachment_id = str(attachment.get("id", ""))
            original_name = str(attachment.get("filename", ""))
            if not re.fullmatch(r"[0-9]+", attachment_id):
                continue
            suffix = Path(original_name).suffix.lower()
            if suffix not in SUPPORTED_SOURCE_EXTENSIONS:
                continue
            declared_size = int(attachment.get("size") or 0)
            if declared_size > MAX_ATTACHMENT_BYTES:
                raise ValueError(f"Attachment is too large: {original_name}")
            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(original_name).name)
            safe_name = safe_name.strip("._") or f"attachment{suffix}"
            stored_name = f"{attachment_id}-{safe_name}"
            data = self._download_attachment(attachment_id)
            total += len(data)
            if total > MAX_TOTAL_ATTACHMENT_BYTES:
                raise ValueError("Supported Jira attachments exceed the 3 MB total limit.")
            (destination / stored_name).write_bytes(data)
            manifest.append({
                "id": attachment_id,
                "originalName": original_name,
                "storedName": stored_name,
                "mimeType": str(attachment.get("mimeType", "")),
                "size": len(data),
            })
        return manifest

    def _download_attachment(self, attachment_id: str) -> bytes:
        url = self.base + f"/rest/api/3/attachment/content/{attachment_id}"
        request = Request(url, headers={
            "Authorization": self._authorization,
            "Accept": "application/octet-stream",
        })
        try:
            with build_opener(SafeAtlassianRedirect()).open(request, timeout=45) as response:
                data = response.read(MAX_ATTACHMENT_BYTES + 1)
        except HTTPError as exc:
            raise ValueError(f"Could not download Jira attachment (HTTP {exc.code}).") from None
        except (URLError, TimeoutError):
            raise ValueError("Could not download Jira attachment.") from None
        if len(data) > MAX_ATTACHMENT_BYTES:
            raise ValueError("Downloaded Jira attachment exceeds the 1 MB limit.")
        if b"\x00" in data[:4096]:
            raise ValueError("A supported attachment appears to be binary.")
        return data


class SafeAtlassianRedirect(HTTPRedirectHandler):
    """Allow Atlassian media redirects without forwarding Jira credentials."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        hostname = (parsed.hostname or "").lower()
        allowed = parsed.scheme == "https" and (
            hostname.endswith(".atlassian.net") or hostname.endswith(".atlassian.com")
        )
        if not allowed:
            raise HTTPError(newurl, code, "Unsafe attachment redirect", headers, fp)
        return Request(newurl, headers={"Accept": "application/octet-stream"})
