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
    // Show only the in-game clock, never the device's real-world time.
    let brenaClock=document.getElementById('brena-world-clock');
    if (!brenaClock) {
      brenaClock=document.createElement('span');
      brenaClock.id='brena-world-clock';
      brenaClock.style.cssText='display:block;font-size:11px;opacity:.75;line-height:1.4';
      $('place').insertAdjacentElement('afterend',brenaClock);
    }
    const clock=app.brena && app.brena.rana;
    const validClock=clock && Number.isInteger(clock.day) && clock.day>=1 &&
      Number.isInteger(clock.minute) && clock.minute>=0 && clock.minute<1440;
    brenaClock.hidden=!validClock;
    brenaClock.textContent=validClock?
      ('브레나 · '+clock.day+'일차 '+String(Math.floor(clock.minute/60)).padStart(2,'0')+
       ':'+String(clock.minute%60).padStart(2,'0')):'';
    // Adjacent travel preview only: no automatic movement or invented action.
    let travelPreview=document.getElementById('brena-travel-preview');
    if (!travelPreview) {
      travelPreview=document.createElement('span');
      travelPreview.id='brena-travel-preview';
      travelPreview.style.cssText='display:block;font-size:11px;opacity:.75;line-height:1.4';
      $('place').insertAdjacentElement('afterend',travelPreview);
    }
    const destinations=app.brena && app.brena.destinations;
    const validDestinations=Array.isArray(destinations) && destinations.every(
      d=>d && typeof d.id==='string' && typeof d.name==='string');
    travelPreview.hidden=!validDestinations || destinations.length===0;
    travelPreview.textContent=travelPreview.hidden?'':
      ('인접 장소 · '+destinations.map(d=>d.name).join(' · '));
    const rana=app.brena && app.brena.rana;
    ranaBadge.hidden=!(rana && rana.player_present === true && rana.place_label && rana.activity_label);
    // Never reveal a remote NPC's location/activity to an absent player.
    ranaBadge.textContent=ranaBadge.hidden?'':('라나 · '+rana.activity_label);
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
