"""Interactive Android login. Return only fixed, credential-free UI messages."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import time
from urllib.parse import parse_qs, urlsplit

import siwc_client as client
from android_auth_http import AuthTransportError


def login(private_files, activity, *, timeout=240):
    stage = "로그인 준비"
    try:
        folder = Path(private_files) / "auth"
        host = client.read_or_create_host_id(folder)
        path = folder / "credentials.json"
        previous = client.read_credentials(path) if path.exists() else None
        stage = "휴대폰 콜백 열기"
        result = {}
        class Handler(BaseHTTPRequestHandler):
            timeout = 3

            def do_GET(self):
                url = urlsplit(self.path)
                if url.path != "/auth/callback":
                    self.send_error(404)
                    return
                params = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items() if len(v) == 1}
                # Ignore unrelated browser requests while the real attempt is pending.
                if params.get("state") != attempt.state:
                    self.send_error(400)
                    return
                try:
                    code, cid = client.read_callback(attempt, params)
                    result.update(code=code, client_id=cid, state=attempt.state)
                except client.SIWCError:
                    result["error"] = "권한 승인" if params.get("error") else "브라우저 인증 응답 확인"
                self.send_response(400 if "error" in result else 200)
                self.end_headers()
                self.wfile.write(b"Return to AI Living World.")

            def log_message(self, *_):
                pass

        with HTTPServer(("127.0.0.1", 0), Handler) as receiver:
            attempt = client.create_auth_attempt(host, port=receiver.server_port,
                                                 client_id=previous["client_id"] if previous else None)
            stage = "시스템 브라우저 열기"
            if not activity.openSystemBrowser(attempt.url):
                return "시스템 브라우저를 열지 못했어. 기본 브라우저 설정을 확인해줘."
            stage = "브라우저에서 앱으로 돌아오기"
            deadline = time.monotonic() + timeout
            while not result:
                receiver.timeout = deadline - time.monotonic()
                if receiver.timeout <= 0:
                    return "브라우저 인증 응답을 기다리다 시간이 지났어. 로그인을 다시 시작해줘."
                receiver.handle_request()
        if "error" in result:
            return result["error"] + " 단계에서 로그인을 마치지 못했어."
        stage = "인증 코드 교환"
        tokens = client.exchange_authorization_code(attempt, result["code"], result["client_id"])
        stage = "인증 서버 정보 확인"
        oidc = client._json_request(client.AUTH_BASE + "/.well-known/openid-configuration")
        uri = oidc.get("jwks_uri", "")
        if not uri.startswith(client.AUTH_BASE + "/"):
            return "인증 서버의 서명 키 주소를 확인하지 못했어."
        stage = "서명 키 조회"
        keys = client._json_request(uri)
        stage = "계정 서명과 구독 권한 확인"
        credentials = client.finalize_tokens(attempt, result, tokens, keys)
        if previous and previous["subject"] != credentials["subject"]:
            return "기존에 연결한 계정과 달라. 같은 ChatGPT 계정으로 로그인해줘."
        stage = "인증 결과 저장"
        client.write_credentials(path, credentials)
        return "인증 확인 완료. GPT 플레이를 눌러줘."
    except AuthTransportError as exc:
        return f"{stage} 실패 · {exc}"
    except Exception:
        return stage + " 단계에서 실패했어."
