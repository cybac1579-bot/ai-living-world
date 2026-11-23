"""Safe, read-only Brena status payload for a future Android VN view.

This is presentation data only; it does not write NPC events, decide player
actions, or fabricate dialogue. Android UI wiring is a separate step.
"""
from __future__ import annotations

from typing import Any
from brena_engine_clock_bridge import view_from_engine_state

KNOWN_ACTIVITIES = {
    "help_villagers": "주민 돕기",
    "spear_training": "창술 훈련",
    "chief_house_life": "촌장 집에서 생활",
    "socializing": "주민 교류",
    "personal_rest": "휴식",
    "idle": "대기",
}

KNOWN_PLACES = {
    "square": "마을 광장",
    "general_store": "잡화점",
    "inn": "여관",
    "smithy": "대장간",
    "chief_house": "촌장 집",
    "guard_training_ground": "경비대 훈련장",
}


def rana_status_payload(engine_state: dict[str, Any], *, seed: int = 1,
                        player_place: str | None = None) -> dict[str, Any]:
    """Only public NPC status, with no invented speech or relationship claims."""
    # Never use a projected NPC location to claim the authoritative engine
    # moved her. Colocation is determined only by the persisted EventStore.
    actual_player = engine_state.get("player", {}).get("location")
    actual_rana = engine_state.get("npcs", {}).get("BRENA-RANA", {}).get("location")
    present = (isinstance(actual_player, str) and
               isinstance(actual_rana, str) and actual_player == actual_rana)
    view = view_from_engine_state(engine_state, "rana", seed=seed, player_place=player_place)
    # The prototype routine is informational until NPC movement events are
    # committed through the original engine. Never show a contradictory place.
    actual_place = actual_rana.removeprefix("BRENA-").lower().replace("-", "_") if present else None
    return {
        "npc_id": "rana",
        "name": "라나",
        "day": view.day,
        "minute": view.minute,
        "place_id": actual_place if present and actual_place in KNOWN_PLACES else None,
        "place_label": KNOWN_PLACES.get(actual_place) if present else None,
        "activity_id": view.npc_activity if present and view.npc_activity in KNOWN_ACTIVITIES else None,
        "activity_label": KNOWN_ACTIVITIES.get(view.npc_activity) if present else None,
        "player_present": present,
    }
