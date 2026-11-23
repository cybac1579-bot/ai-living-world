"""Add player-requested ten-minute world advancement through original EventStore.

No wall-clock scheduling, no AI-generated player action, no second time authority.
"""
from pathlib import Path
import sys

def patch(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    anchor = '        if urlsplit(self.path).path == "/api/brena/travel":'
    assert source.count(anchor) == 1, "Brena travel endpoint must be staged first"
    endpoint = '''        if urlsplit(self.path).path == "/api/brena/advance-time":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    return self._respond(413, {"error": "요청 크기가 올바르지 않아."})
                if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                    return self._respond(415, {"error": "JSON만 허용해."})
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict) or set(payload) != {"revision", "minutes"}:
                    raise WorldError("시간 진행 요청 구조가 올바르지 않아.")
                if type(payload["minutes"]) is not int or payload["minutes"] != 10:
                    raise WorldError("현재는 10분 진행만 허용해.")
                if not self.server.bridge.turn_lock.acquire(blocking=False):
                    raise WorldError("이미 처리 중인 행동이 있어.")
                try:
                    state = self.server.bridge.store.load()
                    if type(payload["revision"]) is not int or state["revision"] != payload["revision"]:
                        raise WorldError("화면이 오래됐어. 다시 불러와줘.")
                    self.server.bridge.store.commit(state["revision"], None,
                        {"events": [{"type": "world_advance", "minutes": 10}]}, mode="brena_world_tick")
                finally:
                    self.server.bridge.turn_lock.release()
                return self._respond(200, self.server.bridge.page_state())
            except (WorldError, ValueError, TypeError, UnicodeError, OSError) as exc:
                return self._respond(422, {"error": str(exc)[:240]})
'''
    source = source.replace(anchor, endpoint + anchor, 1)
    path.write_text(source, encoding="utf-8")
    print("BRENA_EXPLICIT_TIME_HTTP_PATCH=PASS", path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_brena_vn_time.py <vn_server.py>")
    patch(Path(sys.argv[1]))
