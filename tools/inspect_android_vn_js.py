"""Inspect existing VN JavaScript state rendering for a safe Rana status widget."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
candidates=[root/"web/app.js",root/"android_native/app/src/main/assets/web/app.js",root/"android_native/app/src/main/python/web/app.js"]
for p in candidates:
    if not p.is_file():
        print("NOT_FOUND",p)
        continue
    lines=p.read_text(encoding="utf-8").splitlines()
    print("VN_JS",p,"LINES",len(lines))
    needles=("api/state","async function","function render","function refresh","textContent","innerHTML","fetch(","world.")
    matches=[i for i,s in enumerate(lines) if any(t in s for t in needles)]
    selected=set()
    for i in matches[:70]:
        selected.update(range(max(0,i-2),min(len(lines),i+4)))
    for i in sorted(selected):
        print(f"{i+1:4} {lines[i][:220]}")
    break
else:
    raise FileNotFoundError("VN JavaScript missing")
