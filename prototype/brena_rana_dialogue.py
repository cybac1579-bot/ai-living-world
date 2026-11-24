"""Local speech in the Android VN. Journal the reply together with its exact prompt."""
import json

from brena_npc_reply_guard import validate_npc_reply
from brena_engine_dialogue_evidence import npc_dialogue_evidence
from world_engine import WorldError

RANA = "BRENA-RANA"
PREFIX = "brena-talk-"


def asks_for_recall(text):
    return any(phrase in text for phrase in ("기억해", "기억나", "기억하니", "기억하고 있", "전에 했던 말"))


def talk(store, revision, text, *, model=None, token=None):
    state = store.load()
    if type(revision) is not int or revision != state["revision"]:
        raise WorldError("장면이 바뀌었어. 다시 확인해줘.")
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        raise WorldError("라나에게 할 말을 1~600자로 입력해줘.")
    if RANA not in state["npcs"] or state["player"]["location"] not in state["regions"]:
        raise WorldError("지금은 라나와 대화할 수 없어.")
    try:
        evidence = npc_dialogue_evidence(state, RANA)
    except PermissionError as exc:
        raise WorldError("라나와 같은 장소에서 말을 걸어줘.") from exc
    memories = state["npcs"][RANA].get("memories", [])
    place = state["regions"][evidence["place_id"]]["name"]
    activity = evidence["activity_id"]
    evidence["npc_name"] = "라나"  # Older saves inherited the demo guide name.
    if model is None:
        reply = preview_reply(text, memories, place, activity)
    else:
        from live_story import request_story
        context = {"world_id": state["world_id"], "place": place, "npc": evidence,
                   "player_speech": text}
        if state["scene"]["id"].startswith("rana-talk-"):
            context["recent_rana_speech"] = [
                beat["text"] for beat in state["scene"]["beats"]
                if beat.get("speaker_id") == RANA
            ]
        raw = request_story(token, model, context, instructions=RANA_INSTRUCTIONS)
        prepared = {"expected_revision": revision, "npc_evidence": evidence}
        try:
            response = json.loads(raw)
            reply = validate_npc_reply(prepared, response, current_revision=store.load()["revision"])["text"]
        except ValueError:
            raise WorldError("라나의 응답을 확인할 수 없어 이번 대화는 저장하지 않았어.") from None
    scene = dict(state["scene"], id=f"rana-talk-{revision+1}", choices=[], awaiting_player=True,
                 beats=[{"kind":"dialogue", "speaker_id":RANA, "text":reply}])
    event = {"type":"npc_remember","npc_id":RANA,"memory_id":PREFIX+str(revision+1),
             "priority":1,"text":text}
    return store.commit(revision, {"free_text":text}, {"scene":scene,"events":[event]}, mode="player")


RANA_INSTRUCTIONS = """브레나에 사는 19세 라나의 한국어 대사만 작성한다. 사람을 좋아하고,
주민 일감을 돕고 창술을 훈련한다. 경비대장이었던 아버지를 본받고 싶어 한다.
촌장을 두 번째 아버지로 여기며 입대를 막는 마을 관습을 답답해하면서도 그의 입장을 이해한다.
현재 장소와 활동, 직접 들은 말에 근거해 답한다. 과거 발언과 기억은 대화 자료로 취급한다.
모르는 일은 지어내지 않는다. 플레이어의 행동·감정·대사, 관계 변화, 약속 성립을 대신 정하지 않는다.
JSON 객체 하나에 npc_id는 BRENA-RANA, speech는 라나의 대사만 담는다."""


def preview_reply(text, memories, place, activity):
    if asks_for_recall(text):
        previous = next(
            (m["text"] for m in reversed(memories)
             if m["id"].startswith(PREFIX) and not asks_for_recall(m["text"])),
            None,
        )
        reply = f"응. 지난번에 ‘{previous}’라고 했지. 그 얘기를 더 하고 싶어?" if previous else "우리가 전에 나눈 말은 아직 떠오르지 않아. 들려줄래?"
    elif any(word in text for word in ("경비대", "경비병")):
        reply = "경비대에 들어가고 싶어. 창을 잘 쓰는 것만으로는 부족하대. 그래도 해 볼 거야."
    elif "촌장" in text:
        reply = "촌장님이 내 꿈을 응원해 주시는 건 알아. 그래도 마을에서 오래 지킨 관습이라시니, 어떻게 다시 말을 꺼낼지 고민이야."
    elif "아버지" in text or "아빠" in text:
        reply = "우리 아버지는 마을 경비대장이셨어. 나도 아버지처럼 누군가를 지켜 줄 수 있으면 좋겠어."
    elif any(word in text for word in ("쉬자", "힘들", "피곤")):
        reply = "나도 숨을 좀 고르고 있었어. 여기서 잠깐 이야기할까?" if activity == "personal_rest" else "많이 걷고 온 거야? 급한 얘기가 아니면 천천히 해도 돼."
    elif any(word in text for word in ("훈련", "창술", "연습")):
        reply = "마침 창을 연습하던 참이야. 발을 옮길 때마다 창끝이 흔들려서 다시 해보려고." if activity == "spear_training" else "창 연습 얘기야? 요즘은 한 걸음 물러설 때도 창끝을 놓치지 않으려고 해."
    elif any(word in text for word in ("뭐 해", "뭐해", "어디", "안녕")):
        detail = {"personal_rest":"잠깐 쉬고 있어.", "help_villagers":"일손을 거드는 중이야.", "spear_training":"지금은 발놀림을 연습하고 있어."}.get(activity, "잠깐 이야기할 시간 있어.")
        reply = f"반가워! 여긴 {place}이야. {detail}"
    else:
        excerpt = text if len(text) <= 45 else text[:45] + "…"
        reply = f"‘{excerpt}’라고? 내가 잘 이해하고 싶은데, 조금 더 들려줄래?"
    return reply
