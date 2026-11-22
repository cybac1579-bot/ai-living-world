"""Local-only visual-novel browser bridge for DEMO world + ChatGPT OAuth.

Security: loopback only; whitelist static assets; HTTP Host + Origin checks;
CSRF; OAuth access token never exposed to browser, static files, or logs.
"""
from __future__ import annotations

import argparse
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from http.cookies import SimpleCookie
from urllib.parse import urlsplit, parse_qs

from live_story import authorized_catalog, initial_demo_store, run_turn
from world_engine import render_contract, WorldError
from siwc_client import SIWCError

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
SAMPLE = ROOT / "examples" / "live_demo_world.json"
STORE = ROOT / "my_demo_save"
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/assets/forest.jpg": ("assets/forest.jpg", "image/jpeg"),
}
MAX_BODY = 4096


class StoryBridge:
    def __init__(self, store, *, token=None, models=None, sender=None):
        self.store = store
        self.token = token  # OAuth token stays inside this Python process only.
        self.models = list(models or [])
        self.sender = sender
        self.csrf = secrets.token_urlsafe(32)
        self.turn_lock = threading.Lock()
        self.model_ids = {m["slug"] for m in self.models if isinstance(m, dict) and isinstance(m.get("slug"), str)}

    def page_state(self):
        rendered = render_contract(self.store.load())
        asset = rendered.get("image") or {}
        # Never expose world-supplied filesystem paths or serve unregistered assets.
        if asset.get("id") == "DEMO-IMG-FOREST" and (WEB / "assets/forest.jpg").is_file():
            asset["src"] = "/assets/forest.jpg"
        else:
            rendered["image"] = {"id": None, "src": None, "kind": "missing", "fallback": False}
        return {
            "world": rendered,
            "models": [{"slug": m["slug"], "name": str(m.get("name", m["slug"]))} for m in self.models if isinstance(m, dict) and m.get("slug")],
            "connected": bool(self.token and self.model_ids),
            "csrf": self.csrf,
            "mode": "DEMO",
        }

    def turn(self, payload):
        if not isinstance(payload, dict) or set(payload) != {"revision", "model", "submission", "approve"}:
            raise WorldError("요청 구조가 올바르지 않아.")
        if payload["approve"] is not True:
            raise WorldError("실제 GPT 요청을 승인하지 않았어.")
        if not self.token or not self.model_ids:
            raise WorldError("GPT 연결이 활성화되지 않았어. 오프라인 미리보기야.")
        if not isinstance(payload["model"], str) or payload["model"] not in self.model_ids:
            raise WorldError("현재 ChatGPT 계정에서 허용된 모델이 아니야.")
        submission = payload["submission"]
        if not isinstance(submission, dict) or set(submission) not in ({"choice_id"}, {"free_text"}):
            raise WorldError("선택지 또는 자유 입력 하나만 전달해야 해.")
        # Deny parallel requests before using the model; browser retry disabled.
        if not self.turn_lock.acquire(blocking=False):
            raise WorldError("이미 처리 중인 요청이 있어. 자동 중복 요청을 막았어.")
        try:
            revision = self.store.load()["revision"]
            if type(payload["revision"]) is not int or payload["revision"] != revision:
                raise WorldError("화면이 오래됐어. 최신 세계 상태를 다시 불러와줘.")
            kwargs = {"submission": submission, "model": payload["model"], "token": self.token}
            if self.sender is not None:
                kwargs["sender"] = self.sender
            return run_turn(self.store, **kwargs)
        finally:
            self.turn_lock.release()


class LoopbackServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, bridge, *, bootstrap_secret=None):
        if bootstrap_secret is not None and (not isinstance(bootstrap_secret,str) or len(bootstrap_secret) < 32):
            raise ValueError("invalid app session secret")
        self.bootstrap_secret = bootstrap_secret
        if address[0] != "127.0.0.1":
            raise ValueError("외부 기기에 인증 화면을 공개하지 않기 위해 127.0.0.1만 허용해.")
        self.bridge = bridge
        super().__init__(address, VNHandler)


class VNHandler(BaseHTTPRequestHandler):
    server_version = "ALW-Local/1.2"
    sys_version = ""

    def log_message(self, fmt, *args):
        # No path/body/user text/auth data is logged by this server.
        pass

    def _base(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def _trusted_host(self):
        return self.headers.get("Host", "") == f"127.0.0.1:{self.server.server_port}"

    def _respond(self, status, data, mime="application/json; charset=utf-8", *, extra_headers=None):
        if isinstance(data, (dict, list)):
            raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        elif isinstance(data, str):
            raw = data.encode("utf-8")
        else:
            raw = data
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra_headers or []):
            self.send_header(key, value)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def _has_app_session(self):
        secret = getattr(self.server, 'bootstrap_secret', None)
        if secret is None: return True  # Desktop and Termux v1.1 compatibility.
        cookie = SimpleCookie()
        try: cookie.load(self.headers.get('Cookie', ''))
        except Exception: return False
        val = cookie.get('alw_session')
        return bool(val and secrets.compare_digest(val.value,secret))

    def do_GET(self):
        if not self._trusted_host():
            return self._respond(403, {"error": "허용되지 않은 요청 주소야."})
        parsed = urlsplit(self.path)
        path = parsed.path
        secret = getattr(self.server, 'bootstrap_secret', None)
        if secret is not None and path == '/' and parsed.query:
            qs = parse_qs(parsed.query,keep_blank_values=True)
            if set(qs) != {'access'} or qs['access'] != [secret]:
                return self._respond(403, {"error": "앱 세션이 올바르지 않아."})
            filename, mime = STATIC['/']
            return self._respond(200, (WEB / filename).read_bytes(), mime,
                extra_headers=[('Set-Cookie', f'alw_session={secret}; Path=/; HttpOnly; SameSite=Strict')])
        if not self._has_app_session():
            return self._respond(403, {"error": "Android 앱에서만 열 수 있는 화면이야."})
        if path == "/api/state":
            return self._respond(200, self.server.bridge.page_state())
        if path not in STATIC:
            return self._respond(404, {"error": "존재하지 않는 페이지야."})
        filename, mime = STATIC[path]
        return self._respond(200, (WEB / filename).read_bytes(), mime)

    def do_POST(self):
        if not self._has_app_session():
            return self._respond(403, {"error": "Android 앱에서만 사용할 수 있는 기능이야."})
        if not self._trusted_host() or self.headers.get("Origin", "") != self._base():
            return self._respond(403, {"error": "외부 웹페이지의 요청을 거부했어."})
        if self.headers.get("X-ALW-CSRF") != self.server.bridge.csrf:
            return self._respond(403, {"error": "새로고침 후 다시 요청해줘."})
        if urlsplit(self.path).path != "/api/turn":
            return self._respond(404, {"error": "없는 기능이야."})
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self._respond(415, {"error": "JSON만 허용해."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_BODY:
                return self._respond(413, {"error": "요청 크기가 너무 커."})
            payload = json.loads(self.rfile.read(size))
            self.server.bridge.turn(payload)
            return self._respond(200, self.server.bridge.page_state())
        except (WorldError, SIWCError, ValueError, UnicodeError, OSError) as exc:
            # Exceptions are internally bounded; never reveal raw model responses or tokens.
            return self._respond(422, {"error": str(exc)[:240]})


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI Living World 실제 GPT + 모바일형 미연시 UI (PC 로컬 실행용)")
    parser.add_argument("--store", type=Path, default=STORE)
    parser.add_argument("--offline", action="store_true", help="인증/모델 호출 없는 순수 UI 미리보기")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    store = initial_demo_store(args.store, sample_file=SAMPLE)
    if args.offline:
        token, models = None, []
        print("[미리보기] GPT 호출은 비활성화됐어.")
    else:
        try:
            token, models = authorized_catalog()
        except SIWCError as exc:
            print(f"[인증 오류] {exc}")
            print("기존 연결 검사에서 인증을 확인한 뒤 다시 실행해줘. 유료 API 키로 전환하지 않아.")
            return 2
    bridge = StoryBridge(store, token=token, models=models)
    with LoopbackServer(("127.0.0.1", 0), bridge) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print("\nAI Living World — 세계 엔진 연결 미연시 화면 v1.0")
        print("로컬 주소:", url)
        print("이 주소는 실행 중인 PC에서만 열려. 인증 토큰을 브라우저에 보내지 않아.")
        print("GPT 행동을 선택하면 화면에서 매번 사용 여부를 확인해.")
        print("종료하려면 콘솔에서 Ctrl+C를 눌러줘.\n")
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
