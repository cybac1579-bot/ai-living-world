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

ROUTINES = {
    "spear_training": ("오늘은 발을 옮겨도 창끝이 흔들리지 않게 연습하고 있어.", "거리를 다시 잡는 발놀림을 연습하고 있어."),
    "chief_house_life": ("집안일을 마저 하는 중이야. 물동이부터 채워 두려고.", "오늘 쓸 장작을 추려 놓고 있어."),
    "help_villagers": ("부탁받은 짐을 나눠 옮기는 중이야.", "주민들이 맡긴 물건을 정리하고 있어."),
    "personal_rest": ("오늘은 다리에 힘을 좀 풀고 있어.", "잠깐 쉬면서 손에 잡힌 굳은살을 살펴보고 있어."),
    "socializing": ("마을 사람들하고 오늘 있었던 일을 나누고 있어.", "일을 마친 이웃과 안부를 나누는 중이야."),
}

OBSERVATIONS = {
    "spear_training": ("발을 바꿔 디디고 창끝을 다시 맞춘다.", "뒤로 한 걸음 물러서서 창을 고쳐 쥔다."),
    "chief_house_life": ("물동이를 들고 분주히 오간다.", "마른 장작을 골라 한쪽에 쌓는다."),
    "help_villagers": ("짐을 조금씩 나눠 옮긴다.", "맡아 둔 물건을 가지런히 정리한다."),
    "personal_rest": ("다리를 쭉 펴고 잠시 쉰다.", "손에 잡힌 굳은살을 가만히 살핀다."),
    "socializing": ("이웃의 이야기에 귀를 기울인다.", "일을 마친 주민에게 안부를 묻는다."),
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
    # A projected activity is only observable when its projected location
    # agrees with the authoritative, journaled NPC location.
    saved_activity = engine_state.get("npcs", {}).get("BRENA-RANA", {}).get("brena_activity")
    activity_visible = present and actual_place == view.npc_place
    # Prefer the journaled activity; projected routines are legacy fallback.
    activity = saved_activity if isinstance(saved_activity, str) else (view.npc_activity if activity_visible else None)
    return {
        "npc_id": "rana",
        "name": "라나",
        "day": view.day,
        "minute": view.minute,
        "place_id": actual_place if present and actual_place in KNOWN_PLACES else None,
        "place_label": KNOWN_PLACES.get(actual_place) if present else None,
        "activity_id": activity if present and activity in KNOWN_ACTIVITIES else None,
        "activity_label": KNOWN_ACTIVITIES.get(activity) if present else None,
        "routine_detail": ROUTINES[activity][(view.day - 1 + view.minute // 60) % 2]
                         if present and activity in ROUTINES else None,
        "observation": OBSERVATIONS[activity][(view.day - 1 + view.minute // 60) % 2]
                       if present and activity in OBSERVATIONS else None,
        "player_present": present,
    }
