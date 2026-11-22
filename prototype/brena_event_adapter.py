"""Conservative Brena-to-original-engine NPC movement event adapter.

Produces candidate events for the original EventStore transition, never commits
or changes player location. Missing graph links are skipped rather than
teleporting NPCs. Caller must submit through EventStore validation.
"""
from __future__ import annotations

from typing import Any

from brena_simulation import BrenaWorld


def movement_candidates(world: BrenaWorld, engine_state: dict[str, Any],
                        *, place_to_region: dict[str, str],
                        resident_to_npc: dict[str, str]) -> list[dict[str, str]]:
    regions = engine_state["regions"]
    npcs = engine_state["npcs"]
    events = []
    for resident_id, npc_id in resident_to_npc.items():
        if resident_id not in world.residents or npc_id not in npcs:
            continue
        place = world.residents[resident_id].place
        destination = place_to_region.get(place)
        if destination not in regions:
            continue
        current = npcs[npc_id]["location"]
        if current == destination:
            continue
        # Never skip over intermediate regions or infer an unregistered route.
        if destination not in regions[current].get("neighbors", []):
            continue
        events.append({"type": "npc_move", "npc_id": npc_id, "destination": destination})
    return events
