"""Validate a proposed AI turn, then commit through the v0.2 world engine.

NO network/OAuth/API code.  In production, an authorized client hands its
returned assistant text to this adapter. Only this component may commit it.
"""
from __future__ import annotations

import copy
import json
from typing import Any
from world_engine import EventStore, WorldError, resolve_explicit_movement, resolve_explicit_clue_share, render_contract, validate_state
from autonomy import public_recent_events

MAX_RESPONSE_CHARS = 30000


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise WorldError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str):
    raise WorldError(f"non-finite JSON number rejected: {value}")


def _extract_assistant_text(raw: str | dict) -> str:
    """Accept raw JSON text or a Responses-style assistant message envelope.

    Do NOT concatenate arbitrary fields, tool messages, or untrusted roles.
    """
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, dict):
        raise WorldError("AI response must be text or recognized response envelope")
    if "output" in raw and isinstance(raw["output"], list) and raw.get("object", "response") == "response":
        messages = [m for m in raw["output"] if isinstance(m, dict) and m.get("type") == "message"]
        if len(messages) != 1 or messages[0].get("role") != "assistant":
            raise WorldError("expected exactly one assistant message")
        parts = messages[0].get("content")
        if not isinstance(parts, list) or len(parts) != 1:
            raise WorldError("expected exactly one output_text part")
        part = parts[0]
        if not isinstance(part, dict) or part.get("type") != "output_text" or not isinstance(part.get("text"), str):
            raise WorldError("not an output_text message")
        return part["text"]
    raise WorldError("unrecognized AI response envelope")


def parse_ai_response(raw: str | dict) -> dict:
    """Never extract JSON embedded in prose/Markdown. Require one JSON object.

    `raw` must be an actual model response, not a user-submitted event document.
    """
    text = _extract_assistant_text(raw)
    if not (0 < len(text) <= MAX_RESPONSE_CHARS):
        raise WorldError("AI response too long or empty")
    try:
        obj = json.loads(text, object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant)
    except WorldError:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WorldError("AI response must be a single JSON object") from exc
    if not isinstance(obj, dict) or not set(obj) <= {"events", "scene"} or "events" not in obj:
        raise WorldError("AI response has unauthorized or missing top-level fields")
    return obj


def build_model_context(state: dict, *, submission: dict | None, mode: str = "player") -> dict:
    """Model-visible facts without leaking the entire private NPC knowledge graph.

    The local NPC can use its own knowledge for dialogue.  Other NPCs' private
    knowledge never appears in this turn's prompt. An actual model call requires
    a separate authenticated client, which this module deliberately lacks.
    """
    validate_state(state)
    if mode not in ("player", "npc_tick"):
        raise WorldError("invalid context mode")
    if mode == "player" and not isinstance(submission, dict):
        raise WorldError("player context needs explicit submission")
    if mode == "npc_tick" and submission is not None:
        raise WorldError("npc tick cannot contain player submission")
    # Preflight player intent BEFORE inference. A model must know the actual
    # location after an explicitly selected move; arbitrary free text must not
    # silently become a committed move or leak facts about another location.
    origin_location = state["player"]["location"]
    location = origin_location
    selected_effect = {"type": "none"}
    if mode == "player":
        if set(submission) == {"choice_id"}:
            choice_id = submission["choice_id"]
            if not isinstance(choice_id, str):
                raise WorldError("invalid choice id")
            candidates = [c for c in state["scene"].get("choices", []) if c["id"] == choice_id]
            if len(candidates) != 1:
                raise WorldError("unknown or stale choice")
            selected_effect = copy.deepcopy(candidates[0].get("effect") or {"type": "none"})
            if selected_effect["type"] == "player_move":
                location = selected_effect["destination"]
        elif set(submission) in ({"free_text"}, {"free_text", "move_to"}):
            free_text = submission["free_text"]
            if not isinstance(free_text, str) or not free_text.strip() or len(free_text.strip()) > 1000:
                raise WorldError("invalid free text")
            if "move_to" in submission:
                resolved = resolve_explicit_movement(state, free_text)
                if not isinstance(submission["move_to"], str) or resolved != submission["move_to"]:
                    raise WorldError("unapproved free text movement")
                location = resolved
                selected_effect = {"type": "player_move", "destination": resolved}
            # 'free_text' alone retains v0.7.1 journal semantics (no movement).
        else:
            raise WorldError("invalid player submission")
    local_npcs = []
    for npc in state["npcs"].values():
        if npc["location"] == location:
            local_npcs.append({"id": npc["id"], "name": npc["name"],
                               "location": npc["location"], "mood": npc["mood"],
                               "knowledge": copy.deepcopy(npc["knowledge"]),
                               "memories": copy.deepcopy(sorted(npc.get("memories", []), key=lambda m: (-m["priority"], -m["revision"]))[:15]),
                               "active_goals": copy.deepcopy([g for g in npc.get("goals", []) if g["status"] == "active"][:10]),
                               "name_color": npc["name_color"],
                               "autonomy": copy.deepcopy(npc.get("autonomy"))})
    last_scene = state["scene"]
    authorized_share = None
    if mode == "player" and "free_text" in submission:
        authorized_share = resolve_explicit_clue_share(state, submission["free_text"])
    elif mode == "player" and "choice_id" in submission:
        candidate = next((c for c in state["scene"].get("choices", [])
                          if c["id"] == submission["choice_id"]), None)
        if candidate is not None:
            authorized_share = resolve_explicit_clue_share(state, candidate["label"])
    local_history = [a for a in state.get("player_action_history", []) if a["region"] == location]
    repeated_no_discovery = False
    if len(local_history) >= 2:
        a, b = local_history[-2:]
        repeated_no_discovery = (a["text"].strip() == b["text"].strip() and
            not any(c["region"] == location and c["revision"] >= a["revision"]
                    for c in state.get("discoveries", [])))
    return {
        "mode": mode,
        "revision": state["revision"],
        "world_minutes": state.get("world_minutes", 0),
        "visible_world_events": public_recent_events(state, location),
        "connected_regions": list(state["regions"][location].get("neighbors", [])),
        "world_id": state.get("world_id"),
        "origin_location": {"id": origin_location, "name": state["regions"][origin_location]["name"]},
        "location": {"id": location, "name": state["regions"][location]["name"]},
        "selected_player_effect": selected_effect,
        "allowed_choice_effect_types": ["none", "player_move"],
        "read_only_choice_effect_rule": "Looking, inspecting, investigating, talking, waiting or searching must have effect {\"type\":\"none\"}; only connected-region movement may use player_move.",
        "local_npcs": local_npcs,
        "previous_actions_here": copy.deepcopy([a for a in state.get("player_action_history", []) if a["region"] == location][-8:]),
        "known_discoveries": copy.deepcopy(state.get("discoveries", [])[-20:]),
        "authorized_clue_share": copy.deepcopy(authorized_share),
        "repeated_no_discovery": repeated_no_discovery,
        "already_explored_here": copy.deepcopy([f for f in state.get("discoveries", []) if f["region"] == location][-15:]),
        "visible_scene": {"id": last_scene["id"], "beats": copy.deepcopy(last_scene["beats"]),
                          "choices": [{"id": c["id"], "label": c["label"]} for c in last_scene.get("choices", [])],
                          "awaiting_player": last_scene["awaiting_player"]},
        "player_submission": copy.deepcopy(submission),
        "registered_images": {k: {"type": v["type"]} for k, v in state["images"].items()},
        "rules": [
            "Return EXACTLY one JSON object: {events:[...], scene:{...}} for player turns; "
            "for NPC tick during pending choice use events only.",
            "Never invent or commit player actions, feelings, speech, inventory, or movement.",
            "Use narration beats for situation; dialogue beats only with speaker_id.",
            "Dialogue UI has the same pale blue box for all characters, name colors fixed by ID.",
            "Characters must not know other characters' private facts by default.",
            "NPC memories are private and may not be spoken as facts unless appropriate for that NPC.",
            "Only NPCs themselves can gain goals and memories; never write player goals or emotions.",
            "Choices are proposals, not automatically accepted player decisions.",
            "All non-moving choices must have effect type none. Do not invent inspect/search/talk effect types.",
            "NPC route plans require active NPC goals and an explicit connected path; world clock advances only through the engine.",
            "Do not assume the player witnessed offscreen NPC events or knows another NPC's plans.",
            "Location in this context reflects ONLY the explicit chosen move effect. "
            "For free text, treat movement/other lasting changes as unconfirmed until authorized by the engine.",
            "Use registered image IDs when suitable; never invent a matching illustration.",
            "Do not claim any event has been saved; the engine commits after validating it.",
            "When an investigation reveals a new observable fact, emit one clue_discover event with a stable unique ID, local region, short title and concrete detail. Never repeat an existing discovery.",
            "Read previous_actions_here and already_explored_here: do not repeat identical ashes, trees or scenery with no new observation. If no new information remains, say so plainly and offer a different meaningful course of action.",
            "A newly generated discovery is visible to the player only if the chosen action or local NPC interaction genuinely revealed it. Do not award inventory or player emotion as a clue.",
            "Do not transfer player's newly found clue into NPC knowledge unless the player explicitly told that NPC or the NPC independently observed it on-site.",
            "For a player's direct transfer of an EXISTING clue, use clue_share only if authorized_clue_share gives exactly the npc_id and clue_id; otherwise no clue_share event.",
            "When repeated_no_discovery is true, do not repeat the same description or invent a discovery. State what remains unknown and offer a meaningfully different action.",
        ],
    }


def apply_ai_turn(store: EventStore, *, expected_revision: int, submission: dict | None,
                  ai_response: str | dict, mode: str = "player") -> dict:
    """Parse first, validate and commit next, display only the committed state.

    A stale revision or invalid response changes NO state.
    """
    model_output = parse_ai_response(ai_response)
    new_state = store.commit(expected_revision, submission, model_output, mode=mode)
    return render_contract(new_state)
