import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from orchestrator.jira import JiraClient, SafeAtlassianRedirect, load_settings


class JiraTests(unittest.TestCase):
    def settings(self, **extra):
        return dict(JIRA_BASE_URL="https://teamdefinex.atlassian.net",
                    JIRA_EMAIL="test@example.com", JIRA_API_TOKEN="test-secret", **extra)

    def test_scoped_token_uses_gateway(self):
        client = JiraClient(self.settings(JIRA_CLOUD_ID="cloud-123"))
        self.assertEqual(client.base, "https://api.atlassian.com/ex/jira/cloud-123")

    def test_reject_untrusted_host(self):
        settings = self.settings()
        settings["JIRA_BASE_URL"] = "https://teamdefinex.atlassian.net.evil.example"
        with self.assertRaises(ValueError):
            JiraClient(settings)

    @patch("orchestrator.jira.build_opener")
    def test_authenticated_response(self, opener):
        opener.return_value.open.return_value.__enter__.return_value = io.BytesIO(
            b'{"accountId":"test-account"}')
        JiraClient(self.settings()).check_connection()
        request = opener.return_value.open.call_args.args[0]
        self.assertTrue(request.get_header("Authorization").startswith("Basic "))
        self.assertEqual(request.full_url, "https://teamdefinex.atlassian.net/rest/api/3/myself")

    @patch("orchestrator.jira.build_opener")
    def test_http_errors_do_not_expose_token(self, opener):
        opener.return_value.open.side_effect = HTTPError(
            "https://example.com", 401, "test-secret", {}, None)
        with self.assertRaises(ValueError) as error:
            JiraClient(self.settings()).check_connection()
        self.assertIn("401", str(error.exception))
        self.assertNotIn("test-secret", str(error.exception))

    def test_environment_overrides_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".env").write_text("JIRA_EMAIL=file@example.com\n", encoding="utf-8")
            with patch.dict("os.environ", {"JIRA_EMAIL": "env@example.com"}, clear=True):
                self.assertEqual(load_settings(root)["JIRA_EMAIL"], "env@example.com")

    def test_attachment_download_sanitizes_filename(self):
        client = JiraClient(self.settings())
        with tempfile.TemporaryDirectory() as folder, patch.object(
            client, "_download_attachment", return_value=b"<definitions/>"
        ):
            manifest = client.download_attachments([{
                "id": "42", "filename": "../Customer Service.wsdl",
                "size": 14, "mimeType": "application/xml",
            }], Path(folder))
            self.assertEqual(manifest[0]["storedName"], "42-Customer_Service.wsdl")
            self.assertTrue((Path(folder) / "42-Customer_Service.wsdl").exists())

    def test_redirect_strips_authorization(self):
        redirect = SafeAtlassianRedirect()
        request = redirect.redirect_request(
            type("Request", (), {})(), None, 302, "", {},
            "https://api.media.atlassian.com/file/42",
        )
        self.assertIsNone(request.get_header("Authorization"))

    def test_redirect_rejects_other_hosts(self):
        with self.assertRaises(HTTPError):
            SafeAtlassianRedirect().redirect_request(
                type("Request", (), {})(), None, 302, "", {},
                "https://evil.example/file/42",
            )


if __name__ == "__main__":
    unittest.main()
