"""Add a small read-only Rana activity label to the original VN JavaScript.

Never invent NPC speech, player actions or time progression.
"""
from pathlib import Path
import sys

def patch(path: Path) -> None:
    source=path.read_text(encoding="utf-8")
    anchor="    $('place').textContent=app.world.region.name;"
    if source.count(anchor)!=1:
        raise AssertionError(f"Unexpected VN place renderer in {path}")
    addition="""    // Read-only Brena status. The existing scene and player choices stay intact.
    let ranaBadge=document.getElementById('brena-rana-status');
    if (!ranaBadge) {
      ranaBadge=document.createElement('span');
      ranaBadge.id='brena-rana-status';
      ranaBadge.style.cssText='display:block;font-size:11px;opacity:.8;line-height:1.4';
      $('place').insertAdjacentElement('afterend',ranaBadge);
    }
    const rana=app.brena && app.brena.rana;
    ranaBadge.hidden=!(rana && rana.place_label && rana.activity_label);
    ranaBadge.textContent=ranaBadge.hidden?'':('라나 · '+rana.place_label+' · '+rana.activity_label);
"""
    source=source.replace(anchor,anchor+"\n"+addition,1)
    path.write_text(source,encoding="utf-8")
    print("BRENA_VN_UI=PASS",path)

def main(root: Path) -> None:
    # Web assets copied by Android MainActivity are sourced from the Android assets tree.
    candidates=[root/"web/app.js",root/"android_native/app/src/main/assets/web/app.js"]
    found=[p for p in candidates if p.is_file()]
    if not found:
        raise FileNotFoundError("Original VN app.js missing")
    for p in found:
        patch(p)

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: patch_brena_vn_ui.py <extracted Android root>")
    main(Path(sys.argv[1]))
