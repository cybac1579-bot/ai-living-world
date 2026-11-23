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
# Android 15 sometimes returns a system-owned accessibility window even while
# the Activity remains foreground. Check dumpsys below before deciding failure.
if 'com.ailivingworld.mobile' in packages:
    print('EMULATOR_UI_PACKAGE=PASS')
else:
    print('EMULATOR_UI_PACKAGE=INCONCLUSIVE '+repr(sorted(packages)))
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
# Verify the world actually persisted by the embedded Android EventStore.
# This checks first-run data, not just a bundled asset or a WebView callback.
save_paths=$(adb shell run-as com.ailivingworld.mobile find files -name initial_state.json -type f 2>/dev/null | tr -d '\r' || true)
if [[ -z "$save_paths" ]]; then
  echo "::error::No EventStore initial_state.json found after Android startup"
  exit 1
fi
save_count=$(printf '%s\n' "$save_paths" | grep -c .)
if [[ "$save_count" -ne 1 ]]; then
  echo "::error::Expected one Android EventStore initial state, found $save_count"
  exit 1
fi
adb shell run-as com.ailivingworld.mobile cat "$save_paths" > "$RUNNER_TEMP/alw-initial-world.json"
python - <<'PY'
import json, os
from pathlib import Path
p=Path(os.environ['RUNNER_TEMP'])/'alw-initial-world.json'
state=json.loads(p.read_text(encoding='utf-8'))
assert state['player']['location']=='BRENA-SQUARE', 'Android EventStore did not initialize in Brena'
assert 'BRENA-RANA' in state['npcs'], 'Android initial EventStore state lacks Rana'
print('EMULATOR_BRENA_PERSISTED_FIRST_RUN=PASS')
PY
# A process restart must reuse the same event journal rather than reseed Brena.
# Snapshot the complete EventStore data, not only its immutable seed.
save_dir=${save_paths%/initial_state.json}
for name in state.json events.jsonl; do
  if adb shell run-as com.ailivingworld.mobile test -f "$save_dir/$name"; then
    adb shell run-as com.ailivingworld.mobile cat "$save_dir/$name" > "$RUNNER_TEMP/alw-$name-before"
  fi
done
before_hash=$(sha256sum "$RUNNER_TEMP/alw-initial-world.json" | awk '{print $1}')
adb shell am force-stop com.ailivingworld.mobile
adb shell am start -W -n com.ailivingworld.mobile/.MainActivity
sleep 12
adb shell run-as com.ailivingworld.mobile cat "$save_paths" > "$RUNNER_TEMP/alw-initial-world-after-restart.json"
after_hash=$(sha256sum "$RUNNER_TEMP/alw-initial-world-after-restart.json" | awk '{print $1}')
if [[ "$before_hash" != "$after_hash" ]]; then
  echo "::error::Android initial world changed unexpectedly after process restart"
  exit 1
fi
for name in state.json events.jsonl; do
  if [[ -f "$RUNNER_TEMP/alw-$name-before" ]]; then
    adb shell run-as com.ailivingworld.mobile cat "$save_dir/$name" > "$RUNNER_TEMP/alw-$name-after"
    cmp "$RUNNER_TEMP/alw-$name-before" "$RUNNER_TEMP/alw-$name-after" || {
      echo "::error::Android EventStore $name changed unexpectedly on process restart"
      exit 1
    }
  fi
done
echo "EMULATOR_BRENA_RESTART_INITIAL_STATE=PASS"

if grep -Eq "FATAL EXCEPTION|Process: com\\.ailivingworld\\.mobile" "$RUNNER_TEMP/alw-startup-log.txt"; then
  echo "::error::Android app process crashed"
  exit 1
fi
# Capture the current foreground Activity separately from WebView callbacks.
# Android 15 reports topResumedActivity, while some images only expose
# mResumedActivity or mCurrentFocus. Inspect all supported signals.
foreground=$(adb shell dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity' || true)
if [[ "$foreground" != *"com.ailivingworld.mobile"* ]]; then
  foreground="$foreground $(adb shell dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp' || true)"
fi
echo "EMULATOR_FOREGROUND_ACTIVITY=$foreground"
# A system-owned UI hierarchy is inconclusive, not proof of an app crash.
# Foreground Activity + WebView pageFinished + screenshot are checked independently.
if [[ "$foreground" != *"com.ailivingworld.mobile"* ]]; then
  echo "::error::AI Living World is not the foreground Activity"
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
# Decode PNG scanlines and reject a flat-color screenshot. This does not
# prove Brena is visible; it catches blank/single-color presentation failures.
import io
from collections import Counter
chunks=[]
pos=8
while pos<len(data):
    size=struct.unpack('>I',data[pos:pos+4])[0]
    kind=data[pos+4:pos+8]
    payload=data[pos+8:pos+8+size]
    if kind==b'IDAT': chunks.append(payload)
    pos+=size+12
    if kind==b'IEND': break
raw=zlib.decompress(b''.join(chunks))
# PNG images from Android screencap are normally RGB or RGBA, 8 bits/channel.
bit_depth,color_type=data[24],data[25]
assert bit_depth==8 and color_type in (2,6), f'Unexpected screenshot format: {bit_depth}/{color_type}'
channels=3 if color_type==2 else 4
stride=width*channels
previous=bytearray(stride)
offset=0
colors=set()
for y in range(height):
    filt=raw[offset]; offset+=1
    scan=bytearray(raw[offset:offset+stride]); offset+=stride
    for x in range(stride):
        left=scan[x-channels] if x>=channels else 0
        up=previous[x]
        upper_left=previous[x-channels] if x>=channels else 0
        if filt==1: predictor=left
        elif filt==2: predictor=up
        elif filt==3: predictor=(left+up)//2
        elif filt==4:
            p=left+up-upper_left
            a,b,c=abs(p-left),abs(p-up),abs(p-upper_left)
            predictor=left if a<=b and a<=c else (up if b<=c else upper_left)
        elif filt==0: predictor=0
        else: raise AssertionError(f'Unsupported PNG filter {filt}')
        scan[x]=(scan[x]+predictor)&255
    if y%max(1,height//24)==0:
        for x in range(0,width,max(1,width//24)):
            colors.add(bytes(scan[x*channels:x*channels+3]))
    previous=scan
assert offset==len(raw), 'Unexpected trailing screenshot pixel data'
assert len(colors)>=8, f'Visually blank screenshot: only {len(colors)} sampled colors'
print(f'EMULATOR_SCREENSHOT_PNG=PASS {width}x{height} ({idat} compressed bytes)')
print(f'EMULATOR_SCREENSHOT_NONBLANK=PASS ({len(colors)} sampled colors; scene content still needs review)')
PY
echo "EMULATOR_BOOT_SMOKE=PASS"
