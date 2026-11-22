"""Inspect Android VN UI response injection points without modifying gameplay."""
from pathlib import Path
import sys

root=Path(sys.argv[1])
targets=[
    root/"android_native/app/src/main/python/vn_server.py",
    root/"android_native/app/src/main/python/story_bridge.py",
    root/"android_native/app/src/main/java/com/ailivingworld/mobile/MainActivity.java",
]
tokens=("def do_GET", "def do_POST", "def ", "render", "html", "json.dumps", "jsonify", "send_response", "build_model_context", "state", "WebView", "loadUrl", "loadData", "setContentView")
for path in targets:
    if not path.exists():
        print("MISSING",path)
        continue
    lines=path.read_text(encoding="utf-8").splitlines()
    print("====",path,"lines",len(lines),"====")
    indices=[i for i,line in enumerate(lines) if any(t in line for t in tokens)]
    chosen=set()
    for i in indices[:75]:
        chosen.update(range(max(0,i-2),min(len(lines),i+4)))
    for i in sorted(chosen):
        print(f"{i+1:4}: {lines[i][:200]}")
