"""Compatibility boundary between Brena prototype and the original world engine.

The original EventStore remains the only authoritative Android persistence
mechanism. This module deliberately does not write a second save file.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from brena_simulation import BrenaWorld
from brena_dialogue_context import dialogue_context


@dataclass(frozen=True)
class BrenaView:
    day: int
    minute: int
    npc_id: str
    npc_place: str
    npc_activity: str
    dialogue: dict[str, Any]


def npc_view(world: BrenaWorld, npc_id: str, *, player_place: str | None = None) -> BrenaView:
    """Read-only snapshot for the existing VN presentation layer.

    This is a pure projection, not an event or player action. The UI must
    never infer that a player moved just because an NPC is elsewhere.
    """
    npc = world.residents[npc_id]
    context = dialogue_context(world, npc_id, player_place=player_place)
    return BrenaView(
        day=world.day,
        minute=world.minute,
        npc_id=npc_id,
        npc_place=npc.place,
        npc_activity=npc.activity,
        dialogue=context,
    )


def advance_explicit(world: BrenaWorld, minutes: int) -> BrenaWorld:
    """Return a new state only for an explicit time-advance request.

    Original Android EventStore integration must commit this transition
    through its validated event journal before exposing the new state.
    """
    restored = BrenaWorld.from_json(world.to_json())
    restored.advance_time(minutes)
    return restored
