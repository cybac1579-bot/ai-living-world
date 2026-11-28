"""Run against the patched Android VN bridge without an emulator or socket."""
from pathlib import Path
import json
import sys
import tempfile

android = Path(sys.argv[1]).resolve() / "android_native/app/src/main"
sys.path.insert(0, str(android / "python"))
from vn_server import StoryBridge
from world_engine import EventStore, WorldError

with tempfile.TemporaryDirectory() as directory:
    store = EventStore(Path(directory))
    store.create(json.loads((android/"assets/examples/brena_initial_world.json").read_text()))
    bridge = StoryBridge(store)
    def speak(rev, words):
        bridge.turn(dict(revision=rev, model="brena-rana", approve=False,
                         submission={"free_text":words}))

    def rejected(rev, words):
        before = store.load()
        try:
            speak(rev, words)
        except WorldError:
            assert store.load() == before
        else:
            raise AssertionError("invalid speech accepted")

    rejected(0, "안녕")
    store.commit(0, {"destination":"BRENA-CHIEF-HOUSE"}, {"events":[]}, mode="player_travel")
    rejected(1, " ")
    rejected(1, "가"*601)
    words = "내일 창술 연습 얘기를 더 듣고 싶어."
    speak(1, words)
    first = bridge.page_state()["world"]
    assert first["beats"][0]["speaker"]["name"] == "라나"
    assert "창" in first["beats"][0]["text"]
    rejected(1, words)
    store.cache.unlink(missing_ok=True)
    bridge = StoryBridge(EventStore(Path(directory)))
    speak(2, "지난번 말 기억해?")
    assert words in bridge.page_state()["world"]["beats"][0]["text"]
    assert store.load().get("world_minutes", 0) == first["world_minutes"]
    speak(3, "아까 내가 한 말 기억나?")
    assert words in bridge.page_state()["world"]["beats"][0]["text"]
    speak(4, "아버지는 어떤 분이셨어?")
    assert "경비대장" in bridge.page_state()["world"]["beats"][0]["text"]
    for revision in range(5, 65):
        speak(revision, "안녕")
    assert len(store.load()["npcs"]["BRENA-RANA"]["memories"]) == 60
    saved = store.load()
    store.cache.unlink(missing_ok=True)
    assert EventStore(Path(directory)).load() == saved
    print("PASS Android VN bridge: dialogue, recall, replay, 60-memory limit, revision, colocation")

    # Use the shipped OAuth transport with a synthetic Responses stream.
    # No account, external inference or subscription quota participates in this test.
    import io
    from unittest.mock import patch

    connected = StoryBridge(store, token="test-only", models=[{"slug": "test-model"}])
    latest = store.load()["revision"]
    payload = dict(revision=latest, model="test-model", approve=True,
                   submission={"rana_speech": "오늘은 무슨 일을 해?"})
    def stream(request, timeout):
        request_body = json.loads(request.data)
        evidence = json.loads(request_body["input"][0]["content"])
        assert evidence["npc"]["npc_name"] == "라나"
        assert evidence["npc"]["firsthand_memories"]
        assert evidence["player_speech"] == payload["submission"]["rana_speech"]
        assert "촌장" in request_body["instructions"]
        assert "npcs" not in evidence and "player" not in evidence
        speech = json.dumps({"npc_id": "BRENA-RANA", "speech": "잠시 쉬고 있었어."})
        events = [{"type":"response.output_text.delta", "delta":speech},
                  {"type":"response.completed","response":{"status":"completed"}}]
        return io.BytesIO("".join("data: "+json.dumps(event)+"\n" for event in events).encode())

    with patch("live_story.urllib.request.build_opener") as opener:
        opener.return_value.open.side_effect = stream
        for denied in (dict(approve=False), dict(model="unknown"), dict(revision=latest-1)):
            try:
                connected.turn(dict(payload, **denied))
            except WorldError:
                pass
            else:
                raise AssertionError("invalid online turn accepted")
        assert connected.page_state()["last_rana_response"] is None
        opener.assert_not_called()
        connected.turn(payload)
        opener.return_value.open.assert_called_once()
        receipt = connected.page_state()["last_rana_response"]
        assert receipt["count"] == 1 and receipt["requested_model"] == "test-model"
        assert receipt["completed_at"] > 0
        assert bridge.page_state()["last_rana_response"] is None
        try:
            connected.turn(payload)
        except WorldError:
            assert connected.page_state()["last_rana_response"] == receipt
        else:
            raise AssertionError("stale online turn counted")
        opener.return_value.open.assert_called_once()
        store.cache.unlink()
        restored = EventStore(Path(directory)).load()
        assert restored["scene"]["beats"][0]["text"] == "잠시 쉬고 있었어."
        assert restored["npcs"]["BRENA-RANA"]["memories"][-1]["text"] == "오늘은 무슨 일을 해?"
    print("PASS subscription dialogue bridge with simulated transport, consent and journal replay")

    from brena_rana_dialogue import shared_history
    history = shared_history(store, restored["revision"], "창술 연습 기억나?")
    assert history["earlier"]["player"] == words
    assert "창" in history["earlier"]["rana"]
    assert history["recent"][-1]["rana"] == "잠시 쉬고 있었어."
    # Personal boundaries may affect Rana without inventing the player's feelings.
    rev = restored["revision"]
    speak(rev, "말하기 싫으면 안 해도 돼")
    store.cache.unlink(missing_ok=True)
    saved = store.load()
    assert saved["npcs"]["BRENA-RANA"]["mood"] == "안도"
    assert shared_history(store, rev + 1, "")["stance"] == "편안함"
    player = saved["player"].copy()
    store.commit(rev+1, None, {"events":[{"type":"world_advance","minutes":60}]}, mode="brena_world_tick")
    assert store.load()["player"] == player
    print("PASS archived exchange after eviction, own speech, mood, stance and independent time")

    # Recover a Korean topic despite changed particles, even after memory eviction.
    latest = store.load()["revision"]
    assert shared_history(store, latest, "창술은 기억나?")["earlier"]["player"] == words
    assert shared_history(store, latest, "지난번 유리구슬은 기억나?")["earlier"] is None
    # Use the public conversation path again after time progression and a restart.
    store = EventStore(Path(directory))
    region = store.load()["npcs"]["BRENA-RANA"]["location"]
    if store.load()["player"]["location"] != region:
        store.commit(latest, {"destination":region}, {"events":[]}, mode="player_travel")
    bridge = StoryBridge(store)
    speak(store.load()["revision"], "창술은 발놀림부터 배워 보고 싶어.")
    speak(store.load()["revision"], "창술을 기억해?")
    assert "발놀림부터" in bridge.page_state()["world"]["beats"][0]["text"]
    speak(store.load()["revision"], "지난번 유리구슬은 기억나?")
    assert "떠오르지 않아" in bridge.page_state()["world"]["beats"][0]["text"]
    print("PASS topic recall across particles, recent tie-break, unrelated topic clarification")

    connected = StoryBridge(store, token="test-only", models=[{"slug":"test-model"}])
    question = "경비대장은 기억나?"
    with patch("live_story.request_story", return_value=json.dumps({
        "npc_id":"BRENA-RANA", "speech":"우리 아버지 얘기구나."
    })) as model:
        connected.turn(dict(revision=store.load()["revision"], model="test-model", approve=True,
                            submission={"rana_speech":question}))
        sent = model.call_args.args[2]["shared_history"]
        assert sent["earlier"]["player"] == "아버지는 어떤 분이셨어?"
        assert "경비대장" in sent["earlier"]["rana"]
        assert len(sent["recent"]) == 3
    print("PASS online request carries the older exchange with the original speakers")

    insult = "경비대원이 되겠다는 네 꿈이 우스워"
    speak(store.load()["revision"], insult)
    for greeting in range(4):
        speak(store.load()["revision"], "안녕")
    assert "내 일을" in bridge.page_state()["world"]["beats"][0]["text"]
    store.cache.unlink(missing_ok=True)
    store = EventStore(Path(directory))
    bridge = StoryBridge(store)
    history = shared_history(store, store.load()["revision"], "")
    assert history["stance"] == "거리 두기"
    assert history["stance_exchange"]["player"] == insult
    assert history["stance_exchange"] not in history["recent"]
    assert "진지해" in history["stance_exchange"]["rana"]
    speak(store.load()["revision"], "미안해")
    history = shared_history(store, store.load()["revision"], "")
    assert history["stance"] == "조심스러움"
    assert history["stance_exchange"] == history["recent"][-1]
    assert history["stance_exchange"]["player"] == "미안해"
    print("PASS Rana remembers the cause of distance across restart and accepts an apology cautiously")

    for _ in range(4):
        speak(store.load()["revision"], "안녕")
    assert "천천히" in bridge.page_state()["world"]["beats"][0]["text"]
    store.cache.unlink(missing_ok=True)
    store = EventStore(Path(directory))
    connected = StoryBridge(store, token="test-only", models=[{"slug":"test-model"}])
    with patch("live_story.request_story", return_value=json.dumps({
        "npc_id":"BRENA-RANA", "speech":"응, 오늘은 얘기할 수 있어.", "stance":"편안함"
    })) as model:
        connected.turn(dict(revision=store.load()["revision"], model="test-model", approve=True,
                            submission={"rana_speech":"잠깐 이야기할까?"}))
        sent = model.call_args.args[2]["shared_history"]
        assert sent["distance_exchange"]["player"] == insult
        assert "진지해" in sent["distance_exchange"]["rana"]
        assert sent["stance_exchange"]["player"] == "미안해"
        assert sent["stance_exchange"] not in sent["recent"] and sent["distance_exchange"] not in sent["recent"]
    history = shared_history(store, store.load()["revision"], "")
    assert history["stance"] == "편안함" and history["distance_exchange"] is None
    print("PASS later model turn retains both conflict and apology, then retires the old tone")

    # The two sides of an exchange stay distinct even after several recall requests.
    bridge = StoryBridge(EventStore(Path(directory)))
    for question in ("아까 내가 뭐라고 했지?", "아까 네가 뭐라고 했지?") * 3:
        speak(store.load()["revision"], question)
        line = bridge.page_state()["world"]["beats"][0]["text"]
        expected = "잠깐 이야기할까?" if "내가" in question else "응, 오늘은 얘기할 수 있어."
        assert expected in line, line
    speak(store.load()["revision"], "경비대장은 그때 네가 뭐라고 했지?")
    assert "우리 아버지" in bridge.page_state()["world"]["beats"][0]["text"]
    print("PASS Rana recalls her own answer or the player’s words after intervening recall requests")

with tempfile.TemporaryDirectory() as directory:
    store = EventStore(Path(directory))
    store.create(json.loads((android/"assets/examples/brena_initial_world.json").read_text()))
    # The player stays in the square while Rana goes to the store.
    for revision in range(18):
        state = store.commit(revision, None, {"events":[{"type":"world_advance","minutes":10}]},
                             mode="brena_world_tick")
    assert state["player"]["location"] == "BRENA-SQUARE"
    npc = state["npcs"]["BRENA-RANA"]
    assert npc["location"] == "BRENA-GENERAL-STORE"
    log = npc["brena_routine_history"]
    assert log[-1] == {"day":1, "minute":660, "place_id":npc["location"], "activity_id":"help_villagers"}
    store.cache.unlink()
    store = EventStore(Path(directory))
    store.commit(18, {"destination":npc["location"]}, {"events":[]}, mode="player_travel")
    bridge = StoryBridge(store)
    speak(19, "그동안 뭐 했어?")
    line = bridge.page_state()["world"]["beats"][0]["text"]
    assert "오늘 11시" in line and "잡화점" in line and "일손" in line
    connected = StoryBridge(store, token="test-only", models=[{"slug":"test-model"}])
    with patch("live_story.request_story", return_value=json.dumps({
        "npc_id":"BRENA-RANA", "speech":"응, 아까 일손을 좀 거들었어."
    })) as model:
        connected.turn(dict(revision=20, model="test-model", approve=True,
                            submission={"rana_speech":"그 일은 어디서 했어?"}))
        assert model.call_args.args[2]["routine_history"] == log
    print("PASS Rana recalls independent activity at the store after separation and restart")

    speak(21, "어제는 뭐 했어?")
    assert "떠오르지" in bridge.page_state()["world"]["beats"][0]["text"]
    for revision in range(22, 54):
        state = store.commit(revision, None, {"events":[{"type":"world_advance","minutes":60}]},
                             mode="brena_world_tick")
    npc = state["npcs"]["BRENA-RANA"]
    assert all(entry["day"] == 2 for entry in npc["brena_routine_history"])
    archived = npc["brena_previous_day"]
    assert archived and all(entry["day"] == 1 for entry in archived)
    store.cache.unlink()
    store = EventStore(Path(directory))
    bridge = StoryBridge(store)
    if state["player"]["location"] != npc["location"]:
        store.commit(state["revision"], {"destination":"BRENA-SQUARE"}, {"events":[]}, mode="player_travel")
        if npc["location"] != "BRENA-SQUARE":
            store.commit(store.load()["revision"], {"destination":npc["location"]}, {"events":[]}, mode="player_travel")
    for question, prefix in (("어제는 뭐 했어?", "어제"), ("오늘은 뭐했어?", "오늘")):
        speak(store.load()["revision"], question)
        assert bridge.page_state()["world"]["beats"][0]["text"].startswith(prefix)
    connected = StoryBridge(store, token="test-only", models=[{"slug":"test-model"}])
    with patch("live_story.request_story", return_value=json.dumps({
        "npc_id":"BRENA-RANA", "speech":"어제 일을 묻는구나."
    })) as model:
        connected.turn(dict(revision=store.load()["revision"], model="test-model", approve=True,
                            submission={"rana_speech":"어제 뭐 했어?"}))
        context = model.call_args.args[2]
        assert context["routine_history"] == archived and context["requested_routine_day"] == 1
    print("PASS previous-day recall after eviction and restart, no invented day-one backstory")
