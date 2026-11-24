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
    // Travel is always an explicit user click; reuse the existing approved turn path.
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
    let travelActions=document.getElementById('brena-travel-actions');
    if (!travelActions) {
      travelActions=document.createElement('details');
      travelActions.id='brena-travel-actions';
      travelActions.style.cssText='';
      const travelSummary=document.createElement('summary');
      travelSummary.textContent='이동 · 시간';
      travelActions.appendChild(travelSummary);
      travelPreview.insertAdjacentElement('afterend',travelActions);
    }
    Array.from(travelActions.querySelectorAll('button')).forEach(button=>button.remove());
    if (validDestinations) destinations.forEach(d=>{
      const btn=document.createElement('button');
      btn.type='button';
      btn.textContent='이동 · '+d.name;
      btn.style.cssText='';
      btn.disabled=sending;
      btn.addEventListener('click',()=>{
        if (sending || !app || !app.brena ||
            !Array.isArray(app.brena.destinations) ||
            !app.brena.destinations.some(x=>x.id===d.id)) return;
        // The original resolver accepts exact canonical region IDs.
        // No background action, direct state mutation or synthetic NPC speech.
        // No GPT token, model choice, or artificial world-clock advance.
        if (!window.confirm(d.name+'(으)로 이동할까?')) return;
        sending=true;
        Array.from(travelActions.children).forEach(b=>{b.disabled=true;});
        fetch('/api/brena/travel',{
          method:'POST',
          headers:{'Content-Type':'application/json','X-ALW-CSRF':app.csrf},
          body:JSON.stringify({revision:app.world.revision,destination:d.id})
        }).then(async res=>{
          const data=await res.json();
          if (!res.ok) throw new Error(data.error||'이동 실패');
          sending=false;
          renderScene(data);
        }).catch(async err=>{
          notify('이동 상태를 다시 확인해줘: '+String(err.message||err));
          sending=false;
          try {const res=await fetch('/api/state',{cache:'no-store'});if(res.ok)renderScene(await res.json());}catch(_e){}
        }).finally(()=>{sending=false;});

      });
      travelActions.appendChild(btn);
    });
    travelActions.hidden=!validDestinations && !validClock;
    // The clock advances only after an explicit player click.
    let timeActions=document.getElementById('brena-time-actions');
    if (!timeActions) {
      timeActions=document.createElement('div');
      timeActions.id='brena-time-actions';
      timeActions.style.cssText='';
      travelActions.appendChild(timeActions);
    }
    timeActions.replaceChildren();
    if (validClock) {
      const advanceBtn=document.createElement('button');
      advanceBtn.type='button';
      advanceBtn.textContent='시간 10분 진행';
      advanceBtn.style.cssText='';
      advanceBtn.disabled=sending;
      advanceBtn.addEventListener('click',()=>{
        if (sending || !app || !app.world || !app.csrf) return;
        if (!window.confirm('게임 시간을 10분 진행할까?')) return;
        sending=true;
        advanceBtn.disabled=true;
        fetch('/api/brena/advance-time',{
          method:'POST',
          headers:{'Content-Type':'application/json','X-ALW-CSRF':app.csrf},
          body:JSON.stringify({revision:app.world.revision,minutes:10})
        }).then(async res=>{
          const data=await res.json();
          if (!res.ok) throw new Error(data.error||'시간 진행 실패');
          sending=false;
          renderScene(data);
        }).catch(async err=>{
          notify('시간 진행 상태를 다시 확인해줘: '+String(err.message||err));
          sending=false;
          try {const res=await fetch('/api/state',{cache:'no-store'});if(res.ok)renderScene(await res.json());}catch(_e){}
        }).finally(()=>{sending=false;});
      });
      timeActions.appendChild(advanceBtn);
    }
    timeActions.hidden=!validClock;
    const rana=app.brena && app.brena.rana;
    ranaBadge.hidden=!(rana && rana.player_present === true && rana.place_label);
    // Never reveal a remote NPC's location/activity to an absent player.
    ranaBadge.textContent=ranaBadge.hidden?'':('라나'+(rana.activity_label?' · '+rana.activity_label:''));
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
