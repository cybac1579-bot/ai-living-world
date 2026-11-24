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
        opener.assert_not_called()
        connected.turn(payload)
        opener.return_value.open.assert_called_once()
        store.cache.unlink()
        restored = EventStore(Path(directory)).load()
        assert restored["scene"]["beats"][0]["text"] == "잠시 쉬고 있었어."
        assert restored["npcs"]["BRENA-RANA"]["memories"][-1]["text"] == "오늘은 무슨 일을 해?"
    print("PASS subscription dialogue bridge with simulated transport, consent and journal replay")
