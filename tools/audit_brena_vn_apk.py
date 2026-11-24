"""Validate Brena VN source and packaged APK without running an emulator."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import json
import sys

root=Path(sys.argv[1])
apk=Path(sys.argv[2])
js=(root/"android_native/app/src/main/assets/web/app.js").read_text(encoding="utf-8")
server=(root/"android_native/app/src/main/python/vn_server.py").read_text(encoding="utf-8")
asset_path=root/"android_native/app/src/main/assets/examples/brena_initial_world.json"
initial=json.loads(asset_path.read_text(encoding="utf-8"))
assert initial["player"]["location"]=="BRENA-SQUARE", "Brena must be the first-run player location"
assert "BRENA-RANA" in initial["npcs"], "Brena initial world must contain Rana"
mobile=(root/"android_native/app/src/main/python/mobile_embedded.py").read_text(encoding="utf-8")
java=(root/"android_native/app/src/main/java/com/ailivingworld/mobile/MainActivity.java").read_text(encoding="utf-8")
assert "return private, brena, web" in mobile, "Embedded server does not select Brena sample"
assert "store = initial_demo_store(save,sample_file=sample)" in mobile, "Existing EventStore startup must be preserved"
assert '"examples/brena_initial_world.json"' in java, "Java must copy Brena packaged asset"
assert "brena-time-actions" in js and "/api/brena/advance-time" in js, "Missing explicit time control"
assert "brena-rana-status" in js, "Android VN asset missing Rana label"
assert "ranaBadge.textContent" in js
css=(root/"android_native/app/src/main/assets/web/style.css").read_text(encoding="utf-8")
assert "dataset.brenaSpeaker" in js, "Missing engine-owned dialogue speaker mapping"
assert '[data-brena-speaker="rana"]' in css, "Missing Rana pastel dialogue card"
assert '[data-brena-speaker="leticia"]' in css, "Missing Leticia pale-blue dialogue card"
assert "#panel.narration-panel" in css, "Narration and dialogue must have distinct styles"
assert "const ranaSpeaking = speakerKey === 'rana' && dialogue === true" in js, "Portrait requires Rana dialogue"
assert "assets/characters/rana/neutral.webp" in js, "Portrait must be local"
assert "#brena-rana-portrait[hidden]" in css, "Portrait hidden when unavailable"
assert "const speakerKey = speakerName === '라나' ? 'rana'" in js, "Rana mapping must be exact-name only"
assert "speakerName === '레티시아' ? 'leticia'" in js, "Leticia mapping must be exact-name only"
assert "else delete $('panel').dataset.brenaSpeaker" in js, "Unknown speakers must not inherit Rana or Leticia styling"
assert "brena-travel-preview" in js, "Android VN asset missing adjacent travel preview"
assert "app.brena.destinations" in js, "Android VN travel preview must use server data"
assert "/api/brena/travel" in js, "Travel button must call offline endpoint"
assert 'mode="brena_world_tick"' in server and '"/api/brena/advance-time"' in server, "Missing original EventStore time endpoint"
assert 'mode="player_travel"' in server, "Offline travel must use original EventStore"
assert 'if urlsplit(self.path).path == "/api/brena/travel":' in server, "Missing protected offline route"
assert '"brena": {"rana": rana_status_payload(engine_state),' in server
assert '"destinations": available_destinations(engine_state)' in server
assert "from brena_player_navigation import available_destinations" in server
with ZipFile(apk) as z:
    names=z.namelist()
    brena_assets=[name for name in names if name.endswith("examples/brena_initial_world.json")]
    assert brena_assets, "Compiled APK does not contain Brena first-run world asset"
    assert any(json.loads(z.read(name).decode("utf-8"))["player"]["location"]=="BRENA-SQUARE" for name in brena_assets), "Compiled Brena asset has wrong start"
    portrait=root/"android_native/app/src/main/assets/web/assets/characters/rana/neutral.webp"
    packaged_portraits=[name for name in names if name.endswith("assets/characters/rana/neutral.webp")]
    approved=root.parent/"assets/characters/rana/neutral.webp"
    if approved.is_file():
        assert portrait.exists(), "Approved Rana portrait exists in repository but was not staged"
        assert portrait.read_bytes()==approved.read_bytes(), "Staged Rana portrait differs from repository-approved source"
    if portrait.exists():
        assert packaged_portraits, "Approved Rana portrait was staged but missing from compiled APK"
        assert any(z.read(name)==portrait.read_bytes() for name in packaged_portraits), "Packaged Rana portrait differs from approved source"
        print("RANA_APPROVED_PORTRAIT_IN_APK=PASS")
    else:
        assert not packaged_portraits, "Unexpected portrait packaged without approved staged source"
        print("RANA_APPROVED_PORTRAIT_IN_APK=NOT_YET_AVAILABLE")
    assets=[x for x in names if x.endswith("app.js")]
    print("ANDROID_JS_ASSETS",assets)
    found=False
    found_time=False
    found_travel=False
    found_offline_action=False
    found_speaker_js=False
    found_visual_css=False
    for name in (x for x in names if x.endswith("style.css")):
        style=z.read(name).decode("utf-8")
        if '[data-brena-speaker="rana"]' in style and '[data-brena-speaker="leticia"]' in style:
            found_visual_css=True
    for name in assets:
        content=z.read(name)
        if b"dataset.brenaSpeaker" in content:
            found_speaker_js=True
        if b"brena-rana-status" in content:
            found=True
        if b"brena-time-actions" in content and b"/api/brena/advance-time" in content:
            found_time=True
        if b"brena-travel-preview" in content and b"app.brena.destinations" in content:
            found_travel=True
        if b"/api/brena/travel" in content and b"X-ALW-CSRF" in content:
            found_offline_action=True
    assert found, "Compiled APK does not contain Rana UI JavaScript"
    assert found_time, "Compiled APK missing explicit Brena time control"
    assert found_travel, "Compiled APK does not contain Brena travel preview"
    assert found_offline_action, "Compiled APK lacks offline travel action"
    assert found_speaker_js, "Compiled APK lacks NPC speaker-specific dialogue rendering"
    assert found_visual_css, "Compiled APK lacks pastel NPC dialogue styles"
    packaged_python=[]
    for name in names:
        if not name.endswith((".imy",".zip")):
            continue
        try:
            with ZipFile(BytesIO(z.read(name))) as inner:
                packaged_python.extend(x for x in inner.namelist() if "brena_presentation_payload" in x or "brena_player_navigation" in x)
        except Exception:
            continue
    assert any("brena_presentation_payload" in x for x in packaged_python), "Compiled APK missing Rana Python status module"
    assert any("brena_player_navigation" in x for x in packaged_python), "Compiled APK missing travel Python module"
print("BRENA_ANDROID_UI_PACKAGE_AUDIT=PASS")
