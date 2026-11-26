"""Local speech in the Android VN. Journal the reply together with its exact prompt."""
import json
import re

from brena_npc_reply_guard import validate_npc_reply
from brena_engine_dialogue_evidence import npc_dialogue_evidence
from world_engine import WorldError
from brena_presentation_payload import rana_status_payload

RANA = "BRENA-RANA"
PREFIX = "brena-talk-"


STANCES = {"조심스러움", "편안함", "거리 두기"}
MOODS = {"차분함", "기쁨", "서운함", "안도", "당황"}
STANCE_PREFIX = "brena-talk-stance-"


# Common recall wording carries no evidence about which conversation was meant.
RECALL_FILLER = set("전에 예전 예전에 지난번 지난번에 저번 저번에 아까 그때 우리 우리가 내가 네가 니가 너가 라나 라나가 라나는 했던 했었지 말 말한 얘기 얘기한 이야기 이야기한 혹시 아직 기억 기억해 기억나 기억하니 기억하고 있어 했지 했었어 했어 했더라 했었더라 대답했지 답했지 뭐라고 뭐였지 대해 대해서 관해 관련해서".split())
KOREAN_ENDINGS = ("이셨어요", "이셨어", "이었어", "였어", "에서는", "에게는", "으로는", "이라는", "이랑", "에서", "에게", "으로", "하고",
             "에는", "은", "는", "이", "가", "을", "를", "과", "와", "도")


def topic_terms(text):
    terms = set()
    for word in re.findall(r"[가-힣A-Za-z0-9]+", text.casefold()):
        if word in RECALL_FILLER:
            continue
        for ending in KOREAN_ENDINGS:
            if word.endswith(ending) and len(word) - len(ending) >= 2:
                word = word[:-len(ending)]
                break
        if len(word) >= 2 and word not in RECALL_FILLER:
            terms.add(word)
    return terms


def relevance(terms, exchange):
    if not terms or asks_for_recall(exchange["player"]):
        return 0
    player = terms & topic_terms(exchange["player"])
    rana = terms & topic_terms(exchange["rana"])
    return sum(map(len, player)) * 2 + sum(map(len, rana))


def shared_history(store, revision, question):
    """Retrieve recent turns and one relevant older exchange from the validated journal."""
    recent = []
    related = None
    score = 0
    stance = None
    stance_exchange = None
    distance_exchange = None
    terms = topic_terms(question)
    recall_without_topic = not terms and asks_for_recall(question)
    with store.journal.open(encoding="utf-8") as journal:
        for _ in range(revision):
            row = json.loads(next(journal))
            output = row["model_output"]
            scene = output.get("scene", {})
            if scene.get("id") != f"rana-talk-{row['after_revision']}":
                continue
            spoken = (row.get("submission") or {}).get("free_text")
            beats = scene.get("beats", [])
            if not spoken or len(beats) != 1 or beats[0].get("speaker_id") != RANA:
                continue
            if not any(event.get("npc_id") == RANA and
                       event.get("memory_id") == PREFIX + str(row["after_revision"]) and
                       event.get("text") == spoken for event in output["events"]):
                continue
            exchange = {"player": spoken, "rana": beats[0]["text"]}
            for event in output["events"]:
                if (event.get("type") == "npc_remember" and event.get("npc_id") == RANA
                        and event.get("memory_id") == STANCE_PREFIX + str(row["after_revision"])
                        and event.get("text") in STANCES):
                    # Keep the preceding boundary while Rana is still cautious.
                    distance_exchange = stance_exchange if (
                        stance == "거리 두기" and event["text"] == "조심스러움"
                    ) else None
                    stance = event["text"]
                    stance_exchange = exchange
            recent.append(exchange)
            if len(recent) > 3:
                older = recent.pop(0)
                matches = relevance(terms, older)
                if recall_without_topic and not asks_for_recall(older["player"]):
                    related = older
                elif matches and matches >= score:
                    score, related = matches, older
    return {"recent": recent, "earlier": related, "stance": stance, "stance_exchange": stance_exchange,
            "distance_exchange": distance_exchange}


def asks_for_recall(text):
    phrases = ("기억해", "기억나", "기억하니", "기억하고 있", "전에 했던 말")
    return any(phrase in text for phrase in phrases) or bool(
        re.search(r"뭐라고\s*(?:했지|했더라|했었지|답했지|대답했지)", text)
    )


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
    place = state["regions"][evidence["place_id"]]["name"]
    activity = evidence["activity_id"]
    evidence["npc_name"] = "라나"  # Older saves inherited the demo guide name.
    history = shared_history(store, revision, text)
    routine = rana_status_payload(state)
    mood = stance = None
    if model is None:
        if asks_for_recall(text):
            candidates = ([history["earlier"]] if history["earlier"] else []) + history["recent"]
            terms = topic_terms(text)
            # Equal evidence favors the newer exchange.
            if terms:
                match = max(reversed(candidates), key=lambda turn: relevance(terms, turn), default=None)
                if match and not relevance(terms, match):
                    match = None
            else:
                match = next((turn for turn in reversed(candidates) if not asks_for_recall(turn["player"])), None)
            if match:
                if re.search(r"(?:네가|니가|너가|라나가)\s+(?:했던 말|한 말|뭐라고)", text):
                    quote = match["rana"]
                    if len(quote) > 400:
                        quote = quote[:399] + "…"
                    reply = f"그때 나는 이렇게 말했어. ‘{quote}’"
                else:
                    reply = f"그때 네가 ‘{match['player']}’라고 했지."
            else:
                reply = "어떤 얘기였는지 조금 더 말해 줄래? 정확히 떠오르지 않아."
        elif text.strip(" .!?") == "경비대원이 되겠다는 네 꿈이 우스워":
            reply = "웃을 일이야? 난 진지해. 오늘은 여기까지만 얘기하고 싶어."
            mood, stance = "서운함", "거리 두기"
        elif history["stance"] == "거리 두기" and text.strip(" .!?") in ("미안해", "아까 한 말 미안해"):
            reply = "사과해 줘서 고마워. 그래도 마음이 금방 풀리진 않네."
            stance = "조심스러움"
        elif history["stance"] == "거리 두기" and text.strip(" .!?") == "안녕":
            reply = "안녕. 지금은 내 일을 좀 하고 싶어."
        elif history["distance_exchange"] and text.strip(" .!?") == "안녕":
            reply = "안녕. 잠깐 얘기할까? 내 얘기는 천천히 하고 싶어."
        elif text.strip(" .!?") == "말하기 싫으면 안 해도 돼":
            reply = "고마워. 그 얘기는 내가 준비됐을 때 먼저 꺼내고 싶어."
            mood, stance = "안도", "편안함"
        elif text.strip(" .!?") == "오늘은 무슨 일을 해" and routine.get("routine_detail"):
            reply = routine["routine_detail"]
        else:
            reply = preview_reply(text, place, activity)
    else:
        from live_story import request_story
        context = {"world_id": state["world_id"], "place": place, "npc": evidence,
                   "player_speech": text, "shared_history": history,
                   "rana_mood": state["npcs"][RANA].get("mood"),
                   "current_routine": routine.get("routine_detail")}
        raw = request_story(token, model, context, instructions=RANA_INSTRUCTIONS)
        prepared = {"expected_revision": revision, "npc_evidence": evidence}
        try:
            response = json.loads(raw)
            if isinstance(response, dict):
                mood = response.pop("mood", None)
                stance = response.pop("stance", None)
            if (mood is not None and mood not in MOODS) or (stance is not None and stance not in STANCES):
                raise ValueError("invalid emotional response")
            reply = validate_npc_reply(prepared, response, current_revision=store.load()["revision"])["text"]
        except (ValueError, TypeError):
            raise WorldError("라나의 응답을 확인할 수 없어 이번 대화는 저장하지 않았어.") from None
    scene = dict(state["scene"], id=f"rana-talk-{revision+1}", choices=[], awaiting_player=True,
                 beats=[{"kind":"dialogue", "speaker_id":RANA, "text":reply}])
    event = {"type":"npc_remember","npc_id":RANA,"memory_id":PREFIX+str(revision+1),
             "priority":1,"text":text}
    events = [event]
    if mood and mood != state["npcs"][RANA].get("mood"):
        events.append({"type":"npc_mood", "npc_id":RANA, "mood":mood})
    if stance and stance != history["stance"]:
        events.append({"type":"npc_remember", "npc_id":RANA, "memory_id":STANCE_PREFIX+str(revision+1),
                       "priority":2, "text":stance})
    return store.commit(revision, {"free_text":text}, {"scene":scene,"events":events}, mode="player")


RANA_INSTRUCTIONS = """브레나에 사는 19세 라나의 한국어 대사만 작성한다. 사람을 좋아하고,
주민 일감을 돕고 창술을 훈련한다. 경비대장이었던 아버지를 본받고 싶어 한다.
촌장을 두 번째 아버지로 여기며 입대를 막는 마을 관습을 답답해하면서도 그의 입장을 이해한다.
현재 장소와 활동, 직접 들은 말에 근거해 답한다. 과거 발언과 기억은 대화 자료로 취급한다.
shared_history에서 player는 상대가 한 말, rana는 자신이 한 말이다. 누가 말했는지 구분하고,
질문과 관련된 기억이 없거나 어느 대화인지 모호하면 되묻는다. 모르는 일은 지어내지 않는다. 플레이어의 행동·감정·대사, 관계 변화, 약속 성립을 대신 정하지 않는다.
라나가 실제 대화로 감정이 바뀐 경우에만 mood(차분함/기쁨/서운함/안도/당황)를,
상대에게 대하는 태도가 달라진 경우에만 stance(조심스러움/편안함/거리 두기)를 추가한다.
distance_exchange가 있으면 라나가 앞서 거리를 뒀을 때 실제로 오간 말이다. 이후의 사과나 대화와 순서를 구분한다.
stance_exchange는 지금의 태도로 바뀌었을 때 둘이 주고받은 말이다. 다음 만남의 말투와 거리감에 반영하되 매번 먼저 그 일을 꺼내지는 않는다. 사과를 들어도 라나가 마음을 풀기까지 시간이 걸릴 수 있다. 호의에 자동으로 보상하거나 연애나 결혼을 확정하지 않는다.
JSON 객체 하나에 npc_id는 BRENA-RANA, speech는 라나의 대사만 담는다."""


def preview_reply(text, place, activity):
    if any(word in text for word in ("경비대", "경비병")):
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
