"""Inspect the real Android world clock schema without changing game data.

Printed on CI from the original source ZIP; keeps the next integration tied to
the existing clock rather than inventing a second clock field.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else "src")
for name in ("autonomy.py","tests/test_autonomy_clock.py"):
    path=root/name
    if not path.is_file():
        raise SystemExit(f"Missing authoritative clock source: {name}")
    lines=path.read_text(encoding="utf-8").splitlines()
    print(f"===== {name} ({len(lines)} lines) =====")
    for i,line in enumerate(lines,1):
        if any(t in line.lower() for t in ("clock","time","minute","day","world_advance","advance_clock")):
            a=max(1,i-2);b=min(len(lines),i+3)
            print(f"--- {a}-{b} ---")
            for j in range(a,b+1):
                print(f"{j}: {lines[j-1][:200]}")
                if j>=i+3: break
example=root/"examples"
for file in sorted(example.glob("*.json"))[:3]:
    obj=json.loads(file.read_text(encoding="utf-8"))
    print("EXAMPLE",file.name,"TOP_KEYS",sorted(obj))
    for key,value in obj.items():
        if any(token in key.lower() for token in ("clock","time","day")):
            print("CLOCK_FIELD",key,json.dumps(value,ensure_ascii=False)[:500])
