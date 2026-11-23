"""Validate player-selected Brena travel without moving the player implicitly.

This is a pure boundary: the caller must explicitly submit an approved choice
through the original Android engine. No clock advancement or state mutation.
"""
from __future__ import annotations

from typing import Any


def available_destinations(engine_state: dict[str, Any]) -> list[dict[str, str]]:
    """Return only immediate neighbors of the player's current region."""
    regions = engine_state["regions"]
    current = engine_state["player"]["location"]
    if current not in regions:
        raise ValueError("player is in an unknown region")
    result = []
    for destination in regions[current].get("neighbors", []):
        if destination not in regions:
            raise ValueError("region references an unknown neighbor")
        result.append({"id": destination, "name": regions[destination]["name"]})
    return result


def validate_selected_destination(engine_state: dict[str, Any], destination: str) -> str:
    """Accept only a destination explicitly chosen from adjacent regions."""
    if not isinstance(destination, str):
        raise ValueError("destination must be a region ID")
    allowed = {item["id"] for item in available_destinations(engine_state)}
    if destination not in allowed:
        raise ValueError("destination is not adjacent or was not offered")
    return destination
