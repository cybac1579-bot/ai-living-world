"""Deterministic Brena clock projection from the authoritative Android world state.

Never uses wall-clock time, never commits a second save, and never moves player.
The caller supplies explicit game-time minutes from the original EventStore.
"""
from __future__ import annotations

from brena_simulation import BrenaWorld, MINUTES_PER_DAY


def project_clock(world: BrenaWorld, *, elapsed_minutes: int) -> BrenaWorld:
    """Reconstruct NPC routines from a known initial seed and elapsed game time.

    Use only when the engine's initial clock is aligned to Brena day 1, 08:00.
    Never interpret an absolute epoch timestamp as elapsed game time.
    """
    if type(elapsed_minutes) is not int or elapsed_minutes < 0:
        raise ValueError("elapsed_minutes must be a nonnegative integer")
    if world.day != 1 or world.minute != 480 or world.tick_index != 0:
        raise ValueError("projection requires pristine Brena initial world")
    result = BrenaWorld.from_json(world.to_json())
    remaining = elapsed_minutes
    while remaining:
        step = min(remaining, MINUTES_PER_DAY)
        result.advance_time(step)
        remaining -= step
    return result
