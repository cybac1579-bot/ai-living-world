"""Private, read-only bridge between EventStore and NPC dialogue preparation.

This does not expose NPC memories in /api/state or enable online GPT.
"""
from __future__ import annotations

from typing import Any
from brena_engine_dialogue_evidence import npc_dialogue_evidence


def prepare_npc_turn(store: Any, npc_id: str, player_text: str) -> dict[str, Any]:
    if not isinstance(player_text, str) or not player_text.strip() or len(player_text) > 2000:
        raise ValueError("explicit player text required (up to 2000 characters)")
    if not isinstance(npc_id, str) or not npc_id.startswith("BRENA-"):
        raise ValueError("invalid Brena NPC")
    state = store.load()
    evidence = npc_dialogue_evidence(state, npc_id)
    return {
        "expected_revision": state["revision"],
        "player_text": player_text,
        "npc_evidence": evidence,
        "response_constraints": (
            "Generate NPC speech only. Do not create player speech, action, "
            "emotion, consent, location changes, or unobserved memories."
        ),
    }
