"""Report validated original Android region IDs and graph edges for Brena integration.

This inventory is read-only and never invents Brena-to-engine mappings.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "src")
sys.path.insert(0, str(root))
from world_engine import validate_state

valid = []
for file in sorted((root / "examples").glob("*.json")):
    try:
        state = json.loads(file.read_text(encoding="utf-8"))
        validate_state(state)
    except (ValueError, KeyError, TypeError):
        continue
    if state.get("revision") == 0:
        valid.append((file.name, state))
if not valid:
    raise SystemExit("No validated revision-zero Android fixture")
name, state = valid[0]
regions = state["regions"]
print("ANDROID_REGION_FIXTURE", name)
for region_id, region in sorted(regions.items()):
    neighbors = region.get("neighbors", [])
    print("ANDROID_REGION", json.dumps({
        "id": region_id,
        "name": region.get("name"),
        "neighbors": neighbors,
    }, ensure_ascii=False, sort_keys=True))
for npc_id, npc in sorted(state["npcs"].items()):
    print("ANDROID_NPC", json.dumps({
        "id": npc_id, "location": npc.get("location")
    }, ensure_ascii=False, sort_keys=True))
print("ANDROID_PLAYER_REGION", state["player"]["location"])
print("ANDROID_BRENA_REGION_INVENTORY=PASS")
