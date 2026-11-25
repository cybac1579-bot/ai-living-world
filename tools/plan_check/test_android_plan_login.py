import http.client
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

import android_plan_login as subject


class Browser:
    def __init__(self, consent):
        self.consent = consent

    def openSystemBrowser(self, url):
        params = parse_qs(urlsplit(url).query)
        redirect = urlsplit(params["redirect_uri"][0])
        def deliver():
            for path in ["/favicon.ico", redirect.path + "?state=unrelated",
                         redirect.path + "?" + urlencode(dict(state=params["state"][0], **self.consent))]:
                with_http = http.client.HTTPConnection(redirect.hostname, redirect.port, timeout=3)
                with_http.request("GET", path)
                with_http.getresponse().read()
                with_http.close()
        self.thread = threading.Thread(target=deliver)
        self.thread.start()
        return True


class AndroidLoginTests(unittest.TestCase):
    def run_flow(self, browser):
        with tempfile.TemporaryDirectory() as root:
            message = subject.login(root, browser, timeout=3)
            browser.thread.join(4)
            return message, (Path(root)/"auth/credentials.json").exists()

    def test_accept_after_incidental_requests(self):
        with patch.object(subject.client, "exchange_authorization_code", return_value={}), \
             patch.object(subject.client, "_json_request", return_value={"jwks_uri":subject.client.AUTH_BASE+"/keys"}), \
             patch.object(subject.client, "finalize_tokens", return_value={"subject":"fixture"}):
            msg, saved = self.run_flow(Browser({"code":"fixture", "client_id":"oaiapp_fixture"}))
        self.assertTrue(saved)
        self.assertIn("인증 확인 완료", msg)

    def test_decline(self):
        msg, saved = self.run_flow(Browser({"error":"access_denied"}))
        self.assertFalse(saved)
        self.assertIn("권한 승인", msg)

    def test_exchange_failure_redacted(self):
        with patch.object(subject.client, "exchange_authorization_code", side_effect=ValueError("secret")):
            msg, saved = self.run_flow(Browser({"code":"fixture", "client_id":"oaiapp_fixture"}))
        self.assertFalse(saved)
        self.assertEqual(msg, "인증 코드 교환 단계에서 실패했어.")


if __name__ == "__main__":
    unittest.main()
