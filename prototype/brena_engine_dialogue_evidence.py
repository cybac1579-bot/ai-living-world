"""Read-only NPC dialogue evidence from the authoritative Android EventStore.

No GPT invocation, no invented player actions, and no remote NPC surveillance.
"""
from __future__ import annotations

from typing import Any


def npc_dialogue_evidence(state: dict[str, Any], npc_id: str) -> dict[str, Any]:
    npcs = state.get("npcs", {})
    if npc_id not in npcs:
        raise KeyError("unknown NPC")
    npc = npcs[npc_id]
    player_place = state.get("player", {}).get("location")
    together = isinstance(player_place, str) and bool(player_place.strip()) and player_place == npc.get("location")
    if not together:
        raise PermissionError("NPC dialogue requires actual player colocation")
    memories = npc.get("memories", [])
    if not isinstance(memories, list):
        raise ValueError("invalid NPC memory state")
    firsthand = []
    for memory in memories[-20:]:
        if not isinstance(memory, dict):
            continue
        if str(memory.get("id", "")).startswith("brena-talk-stance-"):
            continue  # Supplied separately as Rana's stance, never as spoken words.
        text = memory.get("text")
        if isinstance(text, str) and text.strip():
            firsthand.append({"text": text, "revision": memory.get("revision")})
    activity = npc.get("brena_activity")
    if not isinstance(activity, str):
        activity = None
    return {
        "npc_id": npc_id,
        "npc_name": npc.get("name", npc_id),
        "world_minutes": state.get("world_minutes", 0),
        "place_id": npc["location"],
        "activity_id": activity,
        "firsthand_memories": firsthand,
        "guidance": (
            "Only use this NPC's firsthand memories and observed current activity. "
            "Do not invent player actions, feelings, consent, dialogue, or unseen events."
        ),
    }
