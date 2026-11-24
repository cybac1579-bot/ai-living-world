"""Check the local HTTP contract across an actual embedded-server restart."""
import http.cookiejar
import json
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request

android = Path(sys.argv[1]).resolve() / "android_native/app/src/main"
sys.path.insert(0, str(android/"python"))
import mobile_embedded

with tempfile.TemporaryDirectory() as directory:
    private = Path(directory)
    assets = private/"resources"
    shutil.copytree(android/"assets", assets)
    client = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def start():
        url = mobile_embedded.start_engine(private, assets, offline=True)
        client.open(url).close()
        return url.split("/?")[0]

    def post(path, **payload):
        state = json.load(client.open(base+"/api/state"))
        return json.load(client.open(Request(base+path, json.dumps(payload).encode(),
            {"Origin":base, "Content-Type":"application/json", "X-ALW-CSRF":state["csrf"]})))

    def say(revision, text):
        return post("/api/turn", revision=revision, model="brena-rana",
                    submission={"free_text":text}, approve=False)["world"]["beats"][0]

    try:
        base = start()
        try:
            say(0,"안녕")
        except HTTPError as exc:
            assert exc.code == 422
        else:
            raise AssertionError("Remote conversation was accepted")
        post("/api/brena/travel",revision=0,destination="BRENA-CHIEF-HOUSE")
        question = "경비대에 들어가고 싶어?"
        reply = say(1,question)
        assert reply["speaker"]["name"] == "라나" and "경비대" in reply["text"]
        assert client.open(base+"/assets/characters/rana/neutral.webp").read(4) == b"RIFF"
        mobile_embedded.stop_engine()
        (private/"saves/DEMO/state.json").unlink(missing_ok=True)
        base = start()
        assert question in say(2,"지난번 말 기억해?")["text"]
        print("PASS Android embedded HTTP boot, travel, speech, portrait, restart and recall")
    finally:
        mobile_embedded.stop_engine()
