"""Exercise the staged Chaquopy engine and shipped WebView assets in Chromium."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from playwright.sync_api import sync_playwright, expect

android = Path(sys.argv[1]).resolve() / "android_native/app/src/main"
sys.path.insert(0, str(android / "python"))
import mobile_embedded


def run(page, private, assets):
    def start():
        page.goto(mobile_embedded.start_engine(private, assets, offline=True))
        page.wait_for_function("document.querySelector('#place').textContent.includes('브레나')")

    def speak(text):
        page.get_by_role("button", name="라나에게 말하기").click()
        page.locator("#free-input").fill(text)
        with page.expect_response(lambda r: r.url.endswith("/api/turn")) as response:
            page.get_by_role("button", name="보내기").click()
        assert response.value.ok, response.value.text()
        return response.value.json()["world"]

    start()
    post = """async () => {
      const state = await (await fetch('/api/state')).json();
      return (await fetch('/api/turn', {method:'POST',
        headers:{'Content-Type':'application/json','X-ALW-CSRF':state.csrf},
        body:JSON.stringify({revision:state.world.revision,model:'brena-rana',
                             submission:{free_text:'안녕'},approve:false})})).status;
    }"""
    assert page.evaluate(post) == 422
    page.on("dialog", lambda dialog: dialog.accept())
    page.locator("#brena-travel-actions summary").click()
    page.locator("#brena-travel-actions button").filter(has_text="촌장").first.click()
    first = speak("내일 창술 연습 이야기를 더 듣고 싶어.")
    assert "창" in first["beats"][0]["text"]
    expect(page.locator("#speaker-flag")).to_have_text("라나")
    expect(page.locator("#brena-rana-portrait")).to_be_visible()
    mobile_embedded.stop_engine()
    (private/"saves/DEMO/state.json").unlink(missing_ok=True)
    start()
    second = speak("지난번에 내가 한 말 기억해?")
    assert "내일 창술 연습 이야기를 더 듣고 싶어." in second["beats"][0]["text"]
    assert second["world_minutes"] == first["world_minutes"]
    assert second["revision"] == first["revision"] + 1

    # A synthetic catalog + transport exercises the connected WebView flow.
    mobile_embedded.stop_engine()
    (private/"auth/credentials.json").write_text("{}")
    url = mobile_embedded.start_engine(private, assets, offline=False,
        catalog=lambda **_: ("test-only", [{"slug":"test-model"}]))
    page.goto(url)
    page.get_by_role("button", name="선택지 보기").click()
    page.get_by_role("button", name="직접 행동하기").click()
    expect(page.locator("#free-input")).to_have_attribute("maxlength", "1000")
    page.locator("#close-sheet").click()
    page.get_by_role("button", name="라나에게 말하기").click()
    expect(page.locator("#free-input")).to_have_attribute("maxlength", "600")
    page.locator("#free-input").fill("오늘은 무슨 일을 해?")
    with patch("live_story.request_story", return_value=json.dumps({
        "npc_id":"BRENA-RANA", "speech":"잠시 쉬고 있었어."
    })) as request:
        with page.expect_response(lambda r: r.url.endswith("/api/turn")) as response:
            page.get_by_role("button", name="보내기").click()
        assert response.value.ok, response.value.text()
        request.assert_called_once()
    expect(page.locator("#speaker-flag")).to_have_text("라나")
    assert response.value.json()["world"]["beats"][0]["text"] == "잠시 쉬고 있었어."



with tempfile.TemporaryDirectory() as temp, sync_playwright() as pw:
    private = Path(temp)
    assets = private/"resources"
    shutil.copytree(android/"assets", assets)
    browser = pw.chromium.launch(executable_path=os.environ.get("CHROMIUM") or shutil.which("chromium"))
    try:
        run(browser.new_page(viewport={"width":412,"height":915}), private, assets)
        print("PASS remote rejection, travel, typed dialogue, speaker, portrait, journal replay, recalled speech")
    finally:
        mobile_embedded.stop_engine()
        browser.close()
