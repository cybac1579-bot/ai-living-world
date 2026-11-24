"""Add optional Rana portrait rendering to the original VN without fake art.

The portrait is only displayed for an actual engine-authored Rana dialogue page
and only when an approved local asset is present. No remote image or inference.
"""
from pathlib import Path
import sys

SCRIPT = r"""
    // A local portrait is optional. Never show a fabricated character image.
    let ranaPortrait=document.getElementById('brena-rana-portrait');
    if (!ranaPortrait) {
      ranaPortrait=document.createElement('img');
      ranaPortrait.id='brena-rana-portrait';
      ranaPortrait.alt='라나';
      ranaPortrait.decoding='async';
      ranaPortrait.hidden=true;
      ranaPortrait.addEventListener('error',()=>{ranaPortrait.hidden=true;});
      // A stale image load must never reveal Rana over another speaker.
      // This remains diagnostic-only and never alters world/player state.
      ranaPortrait.addEventListener('load',()=>{
        if (ranaPortrait.naturalWidth>0 &&
            $('panel').dataset.brenaSpeaker==='rana' &&
            $('panel').classList.contains('dialogue-panel')) {
          ranaPortrait.hidden=false;
        }
      });
      $('panel').insertAdjacentElement('beforebegin',ranaPortrait);
    }
    const ranaSpeaking = speakerKey === 'rana' && dialogue === true;
    // Expose a read-only DOM state for emulator/browser visual regression checks.
    ranaPortrait.dataset.brenaExpectedVisible = ranaSpeaking ? 'true' : 'false';
    if (!ranaSpeaking) {
      ranaPortrait.hidden=true;
    } else {
      // The default portrait stays neutral; do not infer strong emotion from prose.
      const portraitUrl='assets/characters/rana/neutral.webp';
      if (ranaPortrait.getAttribute('src') !== portraitUrl) {
        ranaPortrait.hidden=true;
        ranaPortrait.setAttribute('src',portraitUrl);
      }
      if (ranaPortrait.complete && ranaPortrait.naturalWidth>0) {
        ranaPortrait.hidden=false;
      }
    }
"""
STYLE = """
/* Optional Rana portrait. The source file must be explicitly approved. */
#brena-rana-portrait {
  position: fixed;
  z-index: 1;
  width: min(78vw, 440px);
  max-height: 62dvh;
  object-fit: contain;
  object-position: bottom center;
  bottom: 18dvh;
  right: 0;
  pointer-events: none;
  /* The approved temporary portrait contains a forest backdrop, not alpha.
     Feather its rectangular edges rather than pretending it is a cutout. */
  -webkit-mask-image: radial-gradient(ellipse 76% 77% at 52% 49%, #000 58%, transparent 100%);
  mask-image: radial-gradient(ellipse 76% 77% at 52% 49%, #000 58%, transparent 100%);
  filter: drop-shadow(0 10px 18px rgba(17,15,31,.25));
}
#brena-rana-portrait[hidden] { display: none !important; }
#panel { position: relative; z-index: 2; }
"""

def patch(root: Path) -> None:
    scripts=[p for p in (root/"web/app.js",root/"android_native/app/src/main/assets/web/app.js") if p.is_file()]
    styles=[p for p in (root/"web/style.css",root/"android_native/app/src/main/assets/web/style.css") if p.is_file()]
    if not scripts or not styles:
        raise FileNotFoundError("Original VN web assets missing")
    anchor="    else delete $('panel').dataset.brenaSpeaker;"
    for path in scripts:
        source=path.read_text(encoding="utf-8")
        if source.count(anchor)!=1 or "brena-rana-portrait" in source:
            raise AssertionError(f"Unexpected speaker renderer: {path}")
        path.write_text(source.replace(anchor,anchor+"\n"+SCRIPT,1),encoding="utf-8")
    for path in styles:
        source=path.read_text(encoding="utf-8")
        if "#brena-rana-portrait" in source:
            raise AssertionError(f"Duplicate portrait styling: {path}")
        path.write_text(source+"\n"+STYLE,encoding="utf-8")
    print("BRENA_RANA_PORTRAIT_SLOT=PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: patch_brena_rana_portrait.py <extracted Android root>")
    patch(Path(sys.argv[1]))
