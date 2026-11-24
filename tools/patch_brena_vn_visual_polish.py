"""Improve VN speaker-card readability without substituting unapproved character art.

The existing engine owns speaker identity; narration stays visually distinct.
"""
from pathlib import Path
import sys

STYLE = """
/* Brena relationship-first VN: speaker-specific soft dialogue cards. */
#panel.dialogue-panel {
  background: linear-gradient(160deg, rgba(246,241,250,.96), rgba(235,228,243,.94));
  border: 1px solid rgba(171,149,186,.55);
  border-radius: 18px;
  box-shadow: 0 12px 32px rgba(12,12,26,.27);
  backdrop-filter: blur(9px);
}
#panel.dialogue-panel[data-brena-speaker="leticia"] {
  background: linear-gradient(160deg, rgba(232,244,255,.97), rgba(213,232,251,.95));
  border-color: rgba(127,171,218,.65);
}
#panel.dialogue-panel[data-brena-speaker="rana"] {
  background: linear-gradient(160deg, rgba(255,244,238,.97), rgba(252,229,220,.95));
  border-color: rgba(211,152,132,.60);
}
#panel.narration-panel {
  background: rgba(20,27,39,.88);
  border: 1px solid rgba(224,231,245,.24);
  border-radius: 14px;
}
#speaker-flag { font-weight: 700; letter-spacing: .02em; }
@media (max-width: 480px) {
  #panel.dialogue-panel { border-radius: 14px; }
}
"""

def patch(root: Path) -> None:
    candidates = [root / "web/app.js", root / "android_native/app/src/main/assets/web/app.js"]
    scripts = [p for p in candidates if p.is_file()]
    if not scripts:
        raise FileNotFoundError("VN app.js missing")
    anchor = "    styleSpeaker(dialogue ? p.speaker : null);"
    addition = """    // Speaker is provided by the validated engine, never guessed from prose.
    const speakerName = dialogue && p.speaker && typeof p.speaker.name === 'string'
      ? p.speaker.name.trim() : '';
    const speakerKey = speakerName === '라나' ? 'rana'
      : (speakerName === '레티시아' ? 'leticia' : '');
    if (speakerKey) $('panel').dataset.brenaSpeaker = speakerKey;
    else delete $('panel').dataset.brenaSpeaker;
"""
    for script in scripts:
        source = script.read_text(encoding="utf-8")
        if source.count(anchor) != 1:
            raise AssertionError("unexpected VN speaker renderer")
        script.write_text(source.replace(anchor, anchor + "\n" + addition, 1), encoding="utf-8")
    css_candidates = [root / "web/style.css", root / "android_native/app/src/main/assets/web/style.css"]
    styles = [p for p in css_candidates if p.is_file()]
    if not styles:
        raise FileNotFoundError("VN style.css missing")
    for css in styles:
        source = css.read_text(encoding="utf-8")
        if "Brena relationship-first VN" in source:
            raise AssertionError("duplicate visual patch")
        css.write_text(source + "\n" + STYLE, encoding="utf-8")
    print("BRENA_VN_VISUAL_POLISH=PASS")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_brena_vn_visual_polish.py <extracted root>")
    patch(Path(sys.argv[1]))
