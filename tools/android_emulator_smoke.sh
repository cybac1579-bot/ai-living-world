#!/usr/bin/env bash
set -euo pipefail

APK="src/android_native/app/build/outputs/apk/debug/app-debug.apk"
test -s "$APK"
adb install -r "$APK"
adb logcat -c
adb shell am force-stop com.ailivingworld.mobile || true
adb shell am start -W -n com.ailivingworld.mobile/.MainActivity
sleep 20

adb logcat -d -v time -s ALW_BOOT:I AndroidRuntime:E > "$RUNNER_TEMP/alw-startup-log.txt"
echo "== Android startup log =="
tail -n 120 "$RUNNER_TEMP/alw-startup-log.txt" || true

adb shell uiautomator dump /sdcard/alw-ui.xml > /dev/null
adb shell cat /sdcard/alw-ui.xml > "$RUNNER_TEMP/alw-ui.xml"
echo "== Visible native diagnostic text =="
python - <<'PY'
from xml.etree import ElementTree as ET
import os
from pathlib import Path
root=ET.parse(Path(os.environ['RUNNER_TEMP'])/'alw-ui.xml').getroot()
texts=[el.get('text','') for el in root.iter() if el.get('text')]
packages={el.get('package','') for el in root.iter() if el.get('package')}
assert 'com.ailivingworld.mobile' in packages, 'Foreground UI is not AI Living World: '+repr(sorted(packages))
print('EMULATOR_FOREGROUND_PACKAGE=PASS')
for line in texts:
    print(line[:350])
assert not any('진단 D4' in t for t in texts), 'Debug diagnostics should be hidden in presentation mode after startup'
assert not any('오류 단계' in t or 'WebView 오류' in t for t in texts), 'The app reports a Python/server/WebView startup error'
print('EMULATOR_PRESENTATION_UI=PASS (diagnostic chrome hidden; visual content still requires screenshot review)')
PY

if ! grep -Fq 'WebView pageFinished' "$RUNNER_TEMP/alw-startup-log.txt"; then
  echo "::error::Embedded WebView did not report pageFinished"
  exit 1
fi
echo "EMULATOR_WEBVIEW_PAGE_FINISHED=PASS (does not prove scene rendering)"
if grep -Eq "FATAL EXCEPTION|Process: com\\.ailivingworld\\.mobile" "$RUNNER_TEMP/alw-startup-log.txt"; then
  echo "::error::Android app process crashed"
  exit 1
fi
adb shell screencap -p /sdcard/alw-screen.png
adb pull /sdcard/alw-screen.png "$RUNNER_TEMP/alw-screen.png" > /dev/null
python - <<'PY'
# A pageFinished callback alone does not establish a real screenshot.
# Validate the captured PNG signature, dimensions and compressed image chunks.
import os, struct, zlib
from pathlib import Path
p=Path(os.environ['RUNNER_TEMP'])/'alw-screen.png'
data=p.read_bytes()
assert data.startswith(b'\x89PNG\r\n\x1a\n'), 'Screenshot is not PNG'
pos=8
width=height=0
idat=0
while pos < len(data):
    assert pos+12 <= len(data), 'Truncated PNG chunk'
    size=struct.unpack('>I',data[pos:pos+4])[0]
    kind=data[pos+4:pos+8]
    payload=data[pos+8:pos+8+size]
    crc=struct.unpack('>I',data[pos+8+size:pos+12+size])[0]
    assert len(payload)==size and zlib.crc32(kind+payload)==crc, 'Corrupt screenshot PNG chunk'
    if kind==b'IHDR':
        width,height=struct.unpack('>II',payload[:8])
    if kind==b'IDAT':
        idat+=size
    pos+=12+size
    if kind==b'IEND':
        break
assert width>=320 and height>=320 and idat>1000, f'Invalid screenshot: {width}x{height}, {idat} IDAT bytes'
print(f'EMULATOR_SCREENSHOT_PNG=PASS {width}x{height} ({idat} compressed bytes)')
PY
echo "EMULATOR_BOOT_SMOKE=PASS"
