"""Local speech in the Android VN. Journal the reply together with its exact prompt."""
from brena_engine_dialogue_evidence import npc_dialogue_evidence
from world_engine import WorldError

RANA = "BRENA-RANA"
PREFIX = "brena-talk-"


def asks_for_recall(text):
    return any(phrase in text for phrase in ("기억해", "기억나", "기억하니", "기억하고 있", "전에 했던 말"))


def talk(store, revision, text):
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
    scene = dict(state["scene"], id=f"rana-talk-{revision+1}", choices=[], awaiting_player=True,
                 beats=[{"kind":"dialogue", "speaker_id":RANA, "text":reply}])
    event = {"type":"npc_remember","npc_id":RANA,"memory_id":PREFIX+str(revision+1),
             "priority":1,"text":text}
    return store.commit(revision, {"free_text":text}, {"scene":scene,"events":[event]}, mode="player")
