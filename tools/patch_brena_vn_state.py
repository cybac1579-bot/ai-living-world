"""Integrate Brena read-only status into the existing VN /api/state response.

Only adds a presentation field. No new endpoint, save format, player action,
NPC speech, or change to the original EventStore.
"""
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
    path.write_text(source,encoding="utf-8")
    print("BRENA_VN_STATE_INTEGRATION=PASS",path)

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: patch_brena_vn_state.py <vn_server.py>")
    patch(Path(sys.argv[1]))
