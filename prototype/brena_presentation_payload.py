"""Safe, read-only Brena status payload for a future Android VN view.

This is presentation data only; it does not write NPC events, decide player
actions, or fabricate dialogue. Android UI wiring is a separate step.
"""
from __future__ import annotations

from typing import Any
from brena_engine_clock_bridge import view_from_engine_state

KNOWN_ACTIVITIES = {
    "helping": "주민 돕기",
    "work": "일감 수행",
    "training": "창술 훈련",
    "home": "촌장 집에서 생활",
    "social": "주민 교류",
    "rest": "휴식",
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
    view = view_from_engine_state(engine_state, "rana", seed=seed, player_place=player_place)
    return {
        "npc_id": "rana",
        "name": "라나",
        "day": view.day,
        "minute": view.minute,
        "place_id": view.npc_place,
        "place_label": KNOWN_PLACES.get(view.npc_place, view.npc_place),
        "activity_id": view.npc_activity,
        "activity_label": KNOWN_ACTIVITIES.get(view.npc_activity, view.npc_activity),
        "player_present": view.dialogue["player_present"],
    }
