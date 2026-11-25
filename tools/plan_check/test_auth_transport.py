import hashlib
import base64
import sys
import types
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import android_auth_http as transport
import siwc_client as client


class TransportTests(unittest.TestCase):
    def test_staged_exchange_matches_authorization(self):
        attempt = client.create_auth_attempt("urn:uuid:00000000-0000-4000-8000-000000000001", port=50123)
        approval = parse_qs(urlsplit(attempt.url).query)
        def send(url, body, timeout):
            self.assertEqual(url, "https://auth.openai.com/api/accounts/oauth/token")
            form = parse_qs(body)
            self.assertEqual(form["code"], ["test+code/&"])
            self.assertEqual(form["client_id"], ["oaiapp_test"])
            self.assertEqual(form["redirect_uri"], approval["redirect_uri"])
            challenge = hashlib.sha256(form["code_verifier"][0].encode()).digest()
            self.assertEqual(base64.urlsafe_b64encode(challenge).decode().rstrip("="), approval["code_challenge"][0])
            self.assertEqual(form["resource"], approval["resource"])
            self.assertEqual(form["grant_type"], ["authorization_code"])
            self.assertGreater(timeout, 0)
            return ["200", '{"received":true}']
        bridge = types.SimpleNamespace(jclass=lambda _: types.SimpleNamespace(request=send))
        with patch.dict(sys.modules, java=bridge):
            self.assertEqual(client.exchange_authorization_code(attempt, "test+code/&", "oaiapp_test"), {"received": True})

    def test_error_labels_never_echo_credentials(self):
        cases = [("400", '{"error":"invalid_grant","error_description":"secret"}', "HTTP 400 · invalid_grant"),
                 ("403", '{"error":{"code":"secret"}}', "HTTP 403"), ("429", "secret", "HTTP 429"),
                 ("307", "", "HTTP 307"), ("tls", "secret", "보안 연결 실패"),
                 ("200", "secret", "응답 형식 확인 실패")]
        for status, body, message in cases:
            with self.subTest(status=status), self.assertRaises(transport.AuthTransportError) as exc:
                transport.request("", None, 1, send=lambda *_: [status, body])
            self.assertEqual(str(exc.exception), message)


if __name__ == "__main__":
    unittest.main()
