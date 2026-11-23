"""Create a Brena-specific engine fixture from a validated original schema.

Prototype data only: not activated as an Android save until engine regression passes.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else "src")
sys.path.insert(0, str(root))
from world_engine import validate_state

source = root / "examples" / "live_demo_world.json"
state = json.loads(source.read_text(encoding="utf-8"))
validate_state(state)

places = {
    "square": ("브레나 광장", ["general_store", "inn", "smithy", "chief_house", "guard_training_ground"]),
    "general_store": ("브레나 잡화점", ["square"]),
    "inn": ("브레나 여관", ["square"]),
    "smithy": ("브레나 대장간", ["square"]),
    "chief_house": ("브레나 촌장 집", ["square"]),
    "guard_training_ground": ("브레나 경비대 훈련장", ["square"]),
}
template = deepcopy(next(iter(state["regions"].values())))
state["regions"] = {}
for key, (name, neighbors) in places.items():
    region = deepcopy(template)
    region["id"] = "BRENA-" + key.upper().replace("_", "-")
    region["name"] = name
    region["neighbors"] = ["BRENA-" + n.upper().replace("_", "-") for n in neighbors]
    # Original demo directional exits refer to demo neighbors; they cannot
    # be carried into a different graph. Brena directions are not canon yet.
    region["exits"] = {}
    state["regions"]["BRENA-" + key.upper().replace("_", "-")] = region

state["player"]["location"] = "BRENA-SQUARE"
npc_template = deepcopy(next(iter(state["npcs"].values())))
state["npcs"] = {}
for key, place in {
    "rana": "chief_house",
    "chief": "chief_house",
    "smith": "smithy",
    "shopkeeper": "general_store",
    "innkeeper": "inn",
    "resident_a": "square",
    "resident_b": "square",
}.items():
    npc = deepcopy(npc_template)
    npc["id"] = "BRENA-" + key.upper().replace("_", "-")
    npc["location"] = "BRENA-" + place.upper().replace("_", "-")
    state["npcs"]["BRENA-" + key.upper().replace("_", "-")] = npc

validate_state(state)
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("brena-initial-world.json")
out.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("BRENA_INITIAL_WORLD_VALID=PASS", len(state["regions"]), len(state["npcs"]), out)
