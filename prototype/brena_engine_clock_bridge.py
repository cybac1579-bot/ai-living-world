"""Read-only Brena view bound to original Android EventStore world_minutes.

The engine's world_minutes is elapsed simulation time, not wall-clock time.
Brena's day-one 08:00 is a presentation offset, not a second clock.
"""
from __future__ import annotations

from typing import Any
from brena_simulation import BrenaWorld
from brena_clock_projection import project_clock
from brena_android_boundary import npc_view, BrenaView


def view_from_engine_state(engine_state: dict[str, Any], npc_id: str, *,
                           seed: int = 1, player_place: str | None = None) -> BrenaView:
    minutes = engine_state["world_minutes"]
    if type(minutes) is not int or minutes < 0:
        raise ValueError("invalid original engine world_minutes")
    if type(seed) is not int:
        raise ValueError("seed must be integer")
    world = project_clock(BrenaWorld.new(seed=seed), elapsed_minutes=minutes)
    return npc_view(world, npc_id, player_place=player_place)
