"""Wire offline Rana speech into a staged Android project and its VN client."""
from pathlib import Path
import shutil
import sys


def replace(path, old, new):
    source = path.read_text()
    if source.count(old) != 1:
        raise ValueError(f"Unexpected {path.name} source at {old[:40]}")
    path.write_text(source.replace(old, new))


def stage(root):
    android = root / "android_native/app/src/main"
    for directory in (root, android / "python"):
        shutil.copyfile(Path(__file__).resolve().parents[1]/"prototype/brena_rana_dialogue.py",
                        directory/"brena_rana_dialogue.py")
        live = directory / "live_story.py"
        replace(live, "*, urlopen=None, timeout=120)", "*, urlopen=None, timeout=120, instructions=SYSTEM_INSTRUCTIONS)")
        replace(live, "payload = build_request(model, context)", 'payload = build_request(model, context)\n    payload["instructions"] = instructions')
        engine = directory/"world_engine.py"
        anchor = '            state["npcs"][event["npc_id"]].setdefault("memories", []).append({'
        replace(engine, anchor, '''            memories = state["npcs"][event["npc_id"]].setdefault("memories", [])
            if len(memories) >= 60 and event["memory_id"].startswith("brena-talk-"):
                oldest = next((m for m in memories if m["id"].startswith("brena-talk-")), None)
                if oldest is None:
                    raise WorldError("라나의 기억에 빈자리가 없어.")
                memories.remove(oldest)
''' + anchor)
    java = android/"java/com/ailivingworld/mobile/MainActivity.java"
    replace(java, '"web/assets/forest.jpg",', '"web/assets/forest.jpg","web/assets/characters/rana/neutral.webp",')
    server = android/"python/vn_server.py"
    replace(server, '        if payload["approve"] is not True:', '''        if not self.token and payload["model"] == "brena-rana" and payload["approve"] is False:
            from brena_rana_dialogue import talk
            submission = payload["submission"]
            if not isinstance(submission, dict) or set(submission) != {"free_text"}:
                raise WorldError("라나에게 할 말을 입력해줘.")
            with self.turn_lock:
                return talk(self.store, payload["revision"], submission["free_text"])
        if payload["approve"] is not True:''')
    replace(server, '        if not isinstance(submission, dict) or set(submission) not in', '''        if isinstance(submission, dict) and set(submission) == {"rana_speech"}:
            from brena_rana_dialogue import talk
            if not self.turn_lock.acquire(blocking=False):
                raise WorldError("이미 라나가 대답하고 있어.")
            try:
                return talk(self.store, payload["revision"], submission["rana_speech"],
                            model=payload["model"], token=self.token)
            finally:
                self.turn_lock.release()
        if not isinstance(submission, dict) or set(submission) not in''')
    replace(server, '        asset = rendered.get("image") or {}', '''        for beat in rendered["beats"]:
            if beat.get("speaker", {}).get("id") == "BRENA-RANA":
                beat["speaker"]["name"] = "라나"
        scene_id = rendered["scene_id"]
        if scene_id.startswith("rana-talk-") and (
                scene_id != f"rana-talk-{rendered['revision']}" or
                engine_state["npcs"]["BRENA-RANA"]["location"] != engine_state["player"]["location"]):
            rendered["beats"] = [{"kind":"narration", "text":rendered["region"]["name"]}]
        asset = rendered.get("image") or {}''')
    replace(server, '    "/app.js":', '    "/assets/characters/rana/neutral.webp": ("assets/characters/rana/neutral.webp", "image/webp"),\n    "/app.js":')
    for web in (root/"web", android/"assets/web"):
        js = web/"app.js"
        replace(js, '    const rana=app.brena && app.brena.rana;', '''    const rana=app.brena && app.brena.rana;
    const canTalk = rana && rana.player_present === true;
    $('free-toggle').textContent = canTalk ? '라나에게 말하기' : '직접 입력하기';
    $('free-input').maxLength = canTalk ? 600 : 1000;
    $('free-input').placeholder = canTalk ? '라나에게 하고 싶은 말' : '하고 싶은 행동';
''')
        replace(js, '    if (!isFree) renderChoices();', '''    if (isFree && !app.connected && app.brena?.rana?.player_present) {
      $('sheet-title').textContent='라나에게 말하기';
      $('sheet-notice').textContent='라나가 여기서 들은 말을 기억해.';
    }
    if (!isFree) renderChoices();''')
        replace(js,'    if (!app.connected) {notify(','''    const localTalk = !app.connected && app.brena?.rana?.player_present && typeof submission.free_text === 'string';
    if (!localTalk && !app.connected) {notify(''')
        replace(js,"const model=$('model-select').value;", "const model=localTalk ? 'brena-rana' : $('model-select').value;")
        replace(js,"if (!window.confirm('ChatGPT", "if (!localTalk && !window.confirm('ChatGPT")
        replace(js,"model,submission,approve:true", "model,submission,approve:!localTalk")
        replace(js, "const isFree=next==='free';", "const isFree=next==='free' || next==='rana';")
        replace(js, "if (isFree && !app.connected && app.brena?.rana?.player_present)", "if (next==='rana' || (isFree && !app.connected && app.brena?.rana?.player_present))")
        replace(js, "if (!next) return;", """if (!next) return;
    if (app.connected) {
      $('free-input').maxLength=next==='rana'?600:1000;
      $('free-input').placeholder=next==='rana'?'라나에게 하고 싶은 말':'하고 싶은 행동';
    }""")
        replace(js, "$('choices').replaceChildren();", """$('choices').replaceChildren();
    if (app.connected && app.brena?.rana?.player_present) {
      const action=document.createElement('button');
      action.type='button';
      action.textContent='직접 행동하기';
      action.addEventListener('click',()=>setSheet('free'));
      $('choices').append(action);
    }""")
        replace(js, "setSheet(sheet==='free'?'':'free')", """{
      const target=app.connected && app.brena?.rana?.player_present?'rana':'free';
      setSheet(sheet===target?'':target);
    }""")
        replace(js, "setAttribute('aria-expanded',next==='free')",
                "setAttribute('aria-expanded',next===(app.connected && app.brena?.rana?.player_present?'rana':'free'))")
        replace(js, 'sendTurn({free_text:text});', "sendTurn(sheet==='rana'?{rana_speech:text}:{free_text:text});")
        replace(js, "if (!(app.world.choices||[]).length)", "if (!$('choices').childElementCount)")
        replace(web/"index.html","원하는 행동을 직접 입력해","전달할 내용")


if __name__ == "__main__":
    stage(Path(sys.argv[1]))
