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
    # The Brena tick is a single journaled transition: advance the original
    # authoritative clock and commit adjacent NPC moves together.
    source=source.replace(
        '"world_tick", "player_travel"), "unknown mode")',
        '"world_tick", "player_travel", "brena_world_tick"), "unknown mode")',1)
    source=source.replace(
        'if mode == "world_tick":\n        _require(submission is None',
        'if mode in ("world_tick", "brena_world_tick"):\n        _require(submission is None',1)
    source=source.replace(
        '    if mode == "world_tick":\n        from autonomy import advance_clock',
        '''    if mode == "brena_world_tick":
        from autonomy import advance_clock
        from brena_simulation import BrenaWorld
        from brena_event_adapter import movement_candidates
        advance_clock(result, events[0]["minutes"])
        if state.get("world_minutes", 0) // 60 != result["world_minutes"] // 60:
            projected = BrenaWorld.new(seed=1)
            projected.advance_time(result["world_minutes"])
            place_to_region = {
                "square": "BRENA-SQUARE",
                "general_store": "BRENA-GENERAL-STORE",
                "inn": "BRENA-INN",
                "smithy": "BRENA-SMITHY",
                "chief_house": "BRENA-CHIEF-HOUSE",
                "guard_training_ground": "BRENA-GUARD-TRAINING-GROUND",
            }
            resident_to_npc = {
                "rana": "BRENA-RANA", "chief": "BRENA-CHIEF",
                "smith": "BRENA-SMITH", "shopkeeper": "BRENA-SHOPKEEPER",
                "innkeeper": "BRENA-INNKEEPER", "resident_a": "BRENA-RESIDENT-A",
                "resident_b": "BRENA-RESIDENT-B",
            }
            for event in movement_candidates(projected, result,
                                             place_to_region=place_to_region,
                                             resident_to_npc=resident_to_npc):
                result["npcs"][event["npc_id"]]["location"] = event["destination"]
            # Only persist activities that agree with the journaled NPC location.
            for resident_id, npc_id in resident_to_npc.items():
                if npc_id not in result["npcs"] or resident_id not in projected.residents:
                    continue
                resident = projected.residents[resident_id]
                npc = result["npcs"][npc_id]
                if npc["location"] == place_to_region.get(resident.place):
                    npc["brena_activity"] = resident.activity
                else:
                    npc.pop("brena_activity", None)
        result["revision"] += 1
        validate_state(result)
        return result
    if mode == "world_tick":
        from autonomy import advance_clock''',1)
    assert 'if mode == "brena_world_tick":' in source
    assert 'if mode in ("world_tick", "brena_world_tick"):' in source
    path.write_text(source,encoding="utf-8")
    print("BRENA_OFFLINE_TRAVEL_ENGINE_PATCH=PASS",path)

if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("Usage: patch_brena_world_travel.py <world_engine.py>")
    patch(Path(sys.argv[1]))
