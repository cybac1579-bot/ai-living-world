"""Integrate Brena status and explicit offline travel into original VN server."""
from pathlib import Path
import sys

def patch(path: Path) -> None:
    source=path.read_text(encoding="utf-8")
    old="from world_engine import render_contract, WorldError"
    new=old+"\nfrom brena_presentation_payload import rana_status_payload\nfrom brena_player_navigation import available_destinations"
    if source.count(old)!=1:
        raise AssertionError("Unexpected original VN import")
    source=source.replace(old,new,1)
    old='        rendered = render_contract(self.store.load())'
    new='        engine_state = self.store.load()\n        rendered = render_contract(engine_state)'
    if source.count(old)!=1:
        raise AssertionError("Unexpected original VN state access")
    source=source.replace(old,new,1)
    old='            "world": rendered,'
    new='            "world": rendered,\n            "brena": {"rana": rana_status_payload(engine_state),\n                      "destinations": available_destinations(engine_state)},'
    if source.count(old)!=1:
        raise AssertionError("Unexpected original VN response shape")
    source=source.replace(old,new,1)
    # Explicit offline travel uses the original append-only EventStore commit.
    old='from brena_player_navigation import available_destinations'
    new=old+', validate_selected_destination'
    assert source.count(old)==1
    source=source.replace(old,new,1)
    old='        if urlsplit(self.path).path != "/api/turn":'
    new='''        if urlsplit(self.path).path == "/api/brena/travel":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BODY:
                    return self._respond(413, {"error": "요청 크기가 올바르지 않아."})
                if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                    return self._respond(415, {"error": "JSON만 허용해."})
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict) or set(payload) != {"revision", "destination"}:
                    raise WorldError("이동 요청 구조가 올바르지 않아.")
                if not self.server.bridge.turn_lock.acquire(blocking=False):
                    raise WorldError("이미 처리 중인 행동이 있어.")
                try:
                    state = self.server.bridge.store.load()
                    if type(payload["revision"]) is not int or state["revision"] != payload["revision"]:
                        raise WorldError("화면이 오래됐어. 다시 불러와줘.")
                    destination = validate_selected_destination(state, payload["destination"])
                    self.server.bridge.store.commit(state["revision"],
                        {"destination": destination}, {"events": []}, mode="player_travel")
                finally:
                    self.server.bridge.turn_lock.release()
                return self._respond(200, self.server.bridge.page_state())
            except (WorldError, ValueError, TypeError, UnicodeError, OSError) as exc:
                return self._respond(422, {"error": str(exc)[:240]})
        if urlsplit(self.path).path != "/api/turn":'''
    assert source.count(old)==1
    source=source.replace(old,new,1)
    path.write_text(source,encoding="utf-8")
    print("BRENA_VN_STATE_INTEGRATION=PASS",path)

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: patch_brena_vn_state.py <vn_server.py>")
    patch(Path(sys.argv[1]))
