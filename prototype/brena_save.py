"""Crash-resistant local persistence for the standalone Brena simulation.

Never derive elapsed time from the device clock. A valid previous snapshot
remains available when a new write is interrupted or corrupted.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from brena_simulation import BrenaWorld, PLACES, ACTIVITIES


def _validated(payload: str) -> BrenaWorld:
    world = BrenaWorld.from_json(payload)
    if not isinstance(world.seed, int) or isinstance(world.seed, bool):
        raise ValueError("invalid seed")
    if not isinstance(world.day, int) or isinstance(world.day, bool) or world.day < 1:
        raise ValueError("invalid day")
    if not isinstance(world.minute, int) or isinstance(world.minute, bool) or not 0 <= world.minute < 1440:
        raise ValueError("invalid minute")
    if not isinstance(world.tick_index, int) or isinstance(world.tick_index, bool) or world.tick_index < 0:
        raise ValueError("invalid tick index")
    if not isinstance(world.residents, dict) or "rana" not in world.residents:
        raise ValueError("incomplete world save")
    for key, resident in world.residents.items():
        if resident.key != key or not isinstance(resident.memories, list):
            raise ValueError("invalid resident identity or memories")
        if not all(isinstance(memory, str) for memory in resident.memories):
            raise ValueError("invalid resident memory")
        if resident.place not in PLACES or not isinstance(resident.activity, str):
            raise ValueError("invalid resident location or activity")
    if not isinstance(world.relations, dict) or not isinstance(world.events, list):
        raise ValueError("invalid relationship or event data")
    for event in world.events:
        if not isinstance(event, dict) or not {"day", "minute", "actor", "subject", "detail"} <= event.keys():
            raise ValueError("invalid event record")
        if not isinstance(event["detail"], str):
            raise ValueError("invalid event detail")
    return world


def load_world(path: str | Path) -> BrenaWorld:
    """Load primary, falling back to last validated backup on corruption."""
    primary = Path(path)
    backup = primary.with_name(primary.name + ".bak")
    errors = []
    for candidate in (primary, backup):
        try:
            return _validated(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{candidate.name}: {type(exc).__name__}")
    raise ValueError("no valid world save: " + "; ".join(errors))


def save_world(path: str | Path, world: BrenaWorld) -> None:
    """Atomically replace primary, retaining a validated previous primary.

    The caller controls when game time advances; saving never advances it.
    Existing corrupt primary files are never copied over the backup.
    """
    primary = Path(path)
    primary.parent.mkdir(parents=True, exist_ok=True)
    payload = world.to_json()
    _validated(payload)
    backup = primary.with_name(primary.name + ".bak")
    if primary.exists():
        try:
            previous_payload = primary.read_text(encoding="utf-8")
            _validated(previous_payload)
        except (OSError, UnicodeError, ValueError, KeyError, TypeError):
            pass
        else:
            _atomic_write(backup, previous_payload)
    _atomic_write(primary, payload)


def _atomic_write(destination: Path, payload: str) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=".alw-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
