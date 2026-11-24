"""Read-only, evidence-based dialogue context for the Brena prototype.

This module prepares NPC-visible facts for a future dialogue engine.
It never generates player actions, NPC speech, affection, or consent.
"""
from __future__ import annotations

from typing import Any

from brena_simulation import BrenaWorld, PLACES


def dialogue_context(world: BrenaWorld, npc_id: str, *, player_place: str | None = None) -> dict[str, Any]:
    """Build minimal NPC-specific context without leaking other NPCs' memories.

    player_place is an explicitly supplied observation, not an inferred movement.
    Events are visible only if the NPC directly participated in them.
    """
    if npc_id not in world.residents:
        raise KeyError(f"unknown resident: {npc_id}")
    npc = world.residents[npc_id]
    if player_place is not None and player_place not in PLACES:
        raise ValueError("unknown player location")
    witnessed = [
        {"day": e["day"], "minute": e["minute"], "detail": e["detail"], "actor": e["actor"], "subject": e["subject"]}
        for e in world.events
        if npc_id in (e["actor"], e["subject"])
    ]
    return {
        "npc_id": npc_id,
        "day": world.day,
        "minute": world.minute,
        "npc_place": npc.place,
        "npc_activity": npc.activity,
        "player_present": player_place == npc.place if player_place is not None else None,
        "firsthand_events": witnessed[-20:],
        "npc_view_of_player": dict(world.relations.get(npc_id, {}).get("player", {})),
        "player_view_of_npc": None,  # never reveal private player state as NPC knowledge
        "guidance": (
            "Use only firsthand events as known memories. Do not invent player actions, "
            "speech, feelings, relationship consent, or knowledge of private events."
        ),
    }
