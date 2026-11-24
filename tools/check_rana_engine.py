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
