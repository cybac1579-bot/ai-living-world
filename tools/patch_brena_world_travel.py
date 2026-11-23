"""Patch original engine with a journal-replayable offline travel mode."""
from pathlib import Path
import sys

def patch(path: Path) -> None:
    source=path.read_text(encoding="utf-8")
    old='_require(mode in ("player", "npc_tick", "world_tick"), "unknown mode")'
    new='_require(mode in ("player", "npc_tick", "world_tick", "player_travel"), "unknown mode")'
    assert source.count(old)==1, "Unexpected engine mode guard"
    source=source.replace(old,new,1)
    old='    if mode == "world_tick":\n        _require(submission is None'
    new='    if mode == "player_travel":\n        _require(isinstance(submission, dict) and set(submission) == {"destination"}, "invalid travel request")\n        _require(model_output == {"events": []}, "offline travel cannot invent AI output")\n    if mode == "world_tick":\n        _require(submission is None'
    assert source.count(old)==1, "Unexpected transition validation"
    source=source.replace(old,new,1)
    old='    if mode == "world_tick":\n        from autonomy import advance_clock'
    new='''    if mode == "player_travel":
        from brena_player_navigation import validate_selected_destination
        destination = validate_selected_destination(state, submission["destination"])
        result["player"]["location"] = destination
        result["last_player_input"] = {"free_text": destination + "로 이동한다"}
        result.setdefault("player_action_history", []).append({
            "revision": state["revision"] + 1, "region": destination,
            "text": destination + "로 이동한다", "kind": "free_text"})
        result["player_action_history"] = result["player_action_history"][-20:]
        result["revision"] += 1
        validate_state(result)
        return result
    if mode == "world_tick":
        from autonomy import advance_clock'''
    assert source.count(old)==1, "Unexpected transition branch"
    source=source.replace(old,new,1)
    path.write_text(source,encoding="utf-8")
    print("BRENA_OFFLINE_TRAVEL_ENGINE_PATCH=PASS",path)

if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("Usage: patch_brena_world_travel.py <world_engine.py>")
    patch(Path(sys.argv[1]))
