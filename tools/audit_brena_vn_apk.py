"""Validate Brena VN source and packaged APK without running an emulator."""
from pathlib import Path
from zipfile import ZipFile
from io import BytesIO
import sys

root=Path(sys.argv[1])
apk=Path(sys.argv[2])
js=(root/"android_native/app/src/main/assets/web/app.js").read_text(encoding="utf-8")
server=(root/"android_native/app/src/main/python/vn_server.py").read_text(encoding="utf-8")
assert "brena-rana-status" in js, "Android VN asset missing Rana label"
assert "ranaBadge.textContent" in js
assert '"brena": {"rana": rana_status_payload(engine_state),' in server
assert '"destinations": available_destinations(engine_state)' in server
assert "from brena_player_navigation import available_destinations" in server
with ZipFile(apk) as z:
    names=z.namelist()
    assets=[x for x in names if x.endswith("app.js")]
    print("ANDROID_JS_ASSETS",assets)
    found=False
    for name in assets:
        if b"brena-rana-status" in z.read(name):
            found=True
    assert found, "Compiled APK does not contain Rana UI JavaScript"
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
