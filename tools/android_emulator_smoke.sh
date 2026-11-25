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
# Android system dialogs can cover the game while the Activity remains foreground.
# A launcher ANR was previously captured and incorrectly marked as visual success.
blocking=('isn\'t responding', 'is not responding', 'keeps stopping', 'has stopped', 'System UI isn\'t responding', '응답하지 않습니다', '계속 중단됨')
assert not any(any(marker in t for marker in blocking) for t in texts), 'Blocking Android system error dialog obscures the game'

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
rana_location=state['npcs']['BRENA-RANA'].get('location')
player_location=state['player']['location']
assert isinstance(rana_location,str), 'Rana has no authoritative saved location'
print('EMULATOR_RANA_COLOCATION='+('PRESENT' if rana_location==player_location else 'ABSENT'))
print('EMULATOR_RANA_LOCATION='+rana_location)
print('EMULATOR_PLAYER_LOCATION='+player_location)
print('EMULATOR_RANA_OBSERVATION_EXPECTED='+('VISIBLE' if rana_location==player_location else 'HIDDEN'))
# The initial scene must offer a legal, player-selected route to Rana.
# This only inspects the graph: it never moves the player or commits a turn.
regions=state['regions']
assert player_location in regions and rana_location in regions, 'Missing Brena region'
neighbors=regions[player_location].get('neighbors', [])
assert rana_location in neighbors, 'Rana is unreachable from the first-run player location'
assert player_location in regions[rana_location].get('neighbors', []), 'No return path from Rana location'
print('EMULATOR_RANA_ROUTE_AVAILABLE=PASS (player must explicitly choose travel)')


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
# Check the accessibility tree again at the exact screenshot stage. Android
# system ANR dialogs can appear after the initial UI dump or after restart.
# A killed UIAutomator dump can exit 137 even after a successful app restart.
# Retry that transient exit once, still requiring a fresh, parseable XML.
if adb shell uiautomator dump /sdcard/alw-ui-final.xml > /dev/null; then
  :
else
  status=$?
  [[ $status -eq 137 ]] || exit "$status"
  adb shell rm -f /sdcard/alw-ui-final.xml
  sleep 2
  adb shell uiautomator dump /sdcard/alw-ui-final.xml > /dev/null
fi
adb shell cat /sdcard/alw-ui-final.xml > "$RUNNER_TEMP/alw-ui-final.xml"
python - <<'PY'
import os
from pathlib import Path
from xml.etree import ElementTree as ET
root=ET.parse(Path(os.environ['RUNNER_TEMP'])/'alw-ui-final.xml').getroot()
texts=[node.get('text','') for node in root.iter() if node.get('text')]
descriptions=[node.get('content-desc','') for node in root.iter() if node.get('content-desc')]
visible=texts+descriptions
blocking=("isn't responding", "is not responding", "keeps stopping", "has stopped", "응답하지 않습니다", "계속 중단됨")
assert not any(any(marker in value for marker in blocking) for value in visible), (
    'Android system error dialog is covering the final game screenshot: '+repr(visible[:30])
)
print('EMULATOR_FINAL_SCREEN_DIALOG_CHECK=PASS')
PY
# Capture runner memory pressure near the screenshot decoder.
echo "EMULATOR_HOST_MEMORY_BEFORE_PNG_CHECK"
free -m || true
if [[ -r /sys/fs/cgroup/memory.events ]]; then
  cat /sys/fs/cgroup/memory.events || true
fi
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
# Open the offline action panel without selecting any player action.
# Pixel positions are derived from the known 320x640 emulator viewport.
# This diagnostic is deliberately read-only and must not advance world state.
adb shell input tap 79 582
sleep 2
adb shell screencap -p /sdcard/alw-choices-screen.png
adb pull /sdcard/alw-choices-screen.png "$RUNNER_TEMP/alw-choices-screen.png" > /dev/null
test -s "$RUNNER_TEMP/alw-choices-screen.png"
# A second PNG alone is not evidence that the action panel opened.
# Reject unchanged captures rather than silently reporting a choice-list pass.
if cmp -s "$RUNNER_TEMP/alw-screen.png" "$RUNNER_TEMP/alw-choices-screen.png"; then
  echo "::error::Action-panel tap produced an identical screenshot; UI opening is unverified"
  exit 1
fi
echo "EMULATOR_ACTION_PANEL_SCREEN_CHANGED=PASS (does not assert available choices)"
adb shell run-as com.ailivingworld.mobile cat "$save_paths" > "$RUNNER_TEMP/alw-initial-world-after-choices.json"
cmp "$RUNNER_TEMP/alw-initial-world-after-restart.json" "$RUNNER_TEMP/alw-initial-world-after-choices.json" || {
  echo "::error::Opening the choice list unexpectedly changed the initial world"
  exit 1
}
for name in state.json events.jsonl; do
  if [[ -f "$RUNNER_TEMP/alw-$name-after" ]]; then
    adb shell run-as com.ailivingworld.mobile cat "$save_dir/$name" > "$RUNNER_TEMP/alw-$name-after-choices"
    cmp "$RUNNER_TEMP/alw-$name-after" "$RUNNER_TEMP/alw-$name-after-choices" || {
      echo "::error::Opening the choice list unexpectedly changed EventStore $name"
      exit 1
    }
  fi
done
echo "EMULATOR_ACTION_PANEL_READ_ONLY_CAPTURE=PASS (offline preview may have zero choices)"
# Open the travel menu only; this is not permission to select a destination.
# Keep the screenshot for a human review of the actual Android control.
# Close the action panel using its visible X at (274,340), then open
# the travel <details> summary at (120,120). Coordinates are grounded in
# the archived 320x640 emulator screenshots, not guessed from UI text.
adb shell input tap 274 340
sleep 1
adb shell input tap 120 120
sleep 2
adb shell screencap -p /sdcard/alw-travel-menu.png
adb pull /sdcard/alw-travel-menu.png "$RUNNER_TEMP/alw-travel-menu.png" > /dev/null
test -s "$RUNNER_TEMP/alw-travel-menu.png"
# A screenshot of the Android launcher must never be accepted as game UI.
travel_foreground=$(adb shell dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity' || true)
if [[ "$travel_foreground" != *"com.ailivingworld.mobile"* ]]; then
  echo "::error::Travel menu interaction left the AI Living World Activity: $travel_foreground"
  exit 1
fi
echo "EMULATOR_TRAVEL_MENU_FOREGROUND=PASS"
if cmp -s "$RUNNER_TEMP/alw-screen.png" "$RUNNER_TEMP/alw-travel-menu.png"; then
  echo "::error::Travel menu interaction did not visibly change the screen"
  exit 1
fi
echo "EMULATOR_TRAVEL_MENU_SCREEN_CHANGED=PASS (actual menu content still requires review)"
# The screenshot is useful only while the game remains in the foreground.
# Keep this as a read-only visual smoke; actual travel is tested separately
# with an explicit confirmed destination and journal verification.

adb shell run-as com.ailivingworld.mobile cat "$save_paths" > "$RUNNER_TEMP/alw-initial-world-after-travel-menu.json"
cmp "$RUNNER_TEMP/alw-initial-world-after-restart.json" "$RUNNER_TEMP/alw-initial-world-after-travel-menu.json" || {
  echo "::error::Opening the travel menu unexpectedly changed the initial world"
  exit 1
}
for name in state.json events.jsonl; do
  if [[ -f "$RUNNER_TEMP/alw-$name-after" ]]; then
    adb shell run-as com.ailivingworld.mobile cat "$save_dir/$name" > "$RUNNER_TEMP/alw-$name-after-travel-menu"
    cmp "$RUNNER_TEMP/alw-$name-after" "$RUNNER_TEMP/alw-$name-after-travel-menu" || {
      echo "::error::Opening travel menu unexpectedly changed EventStore $name"
      exit 1
    }
  fi
done
echo "EMULATOR_TRAVEL_MENU_CAPTURE=PASS (menu visibility requires screenshot review)"
# Exercise one explicitly confirmed, deterministic test-player travel.
# Resolve the button bounds from the actual Android accessibility tree.
# A hard-coded y=345 previously hit a different row and missed confirmation.
# This is isolated CI test data, never a real user's world.
adb shell uiautomator dump /sdcard/alw-travel-options.xml > /dev/null
adb shell cat /sdcard/alw-travel-options.xml > "$RUNNER_TEMP/alw-travel-options.xml"
travel_tap=$(python - <<'PY'
import os, re
from pathlib import Path
from xml.etree import ElementTree as ET
root=ET.parse(Path(os.environ['RUNNER_TEMP'])/'alw-travel-options.xml').getroot()
matches=[n for n in root.iter() if n.get('text','').strip()=='이동 · 브레나 촌장 집']
assert len(matches)==1, 'Expected exactly one chief-house travel button, got '+str(len(matches))
bounds=matches[0].get('bounds','')
m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',bounds)
assert m, 'Missing travel button bounds: '+bounds
x1,y1,x2,y2=map(int,m.groups())
assert x2>x1 and y2>y1, 'Empty travel button bounds'
print((x1+x2)//2,(y1+y2)//2)
PY
)
read -r travel_x travel_y <<< "$travel_tap"
echo "EMULATOR_TRAVEL_TARGET=($travel_x,$travel_y)"
adb shell input tap "$travel_x" "$travel_y"
sleep 2
adb shell screencap -p /sdcard/alw-after-travel-tap.png
adb pull /sdcard/alw-after-travel-tap.png "$RUNNER_TEMP/alw-after-travel-tap.png" > /dev/null
adb shell uiautomator dump /sdcard/alw-confirm.xml > /dev/null
adb shell cat /sdcard/alw-confirm.xml > "$RUNNER_TEMP/alw-confirm.xml"
python - <<'PY'
import os
from pathlib import Path
from xml.etree import ElementTree as ET
root=ET.parse(Path(os.environ['RUNNER_TEMP'])/'alw-confirm.xml').getroot()
texts=[node.get('text','') for node in root.iter() if node.get('text')]
assert any('이동할까' in t for t in texts), 'Expected explicit travel confirmation dialog: '+repr(texts[:20])
print('EMULATOR_TRAVEL_CONFIRMATION_VISIBLE=PASS')
PY
# Native Android confirmation dialogs do not reliably accept KEYCODE_ENTER.
# Tap the explicit positive button found in UIAutomator instead.
confirm_tap=$(python - <<'PY'
import os, re
from pathlib import Path
from xml.etree import ElementTree as ET
root=ET.parse(Path(os.environ['RUNNER_TEMP'])/'alw-confirm.xml').getroot()
buttons=[n for n in root.iter() if n.get('class','')=='android.widget.Button']
print('CONFIRM_DIALOG_BUTTONS='+repr([(n.get('text'),n.get('bounds')) for n in buttons]),file=__import__('sys').stderr)
positive=[n for n in buttons if n.get('text','').strip() in ('확인','이동','OK','Ok','확인하기','예','Yes')]
assert len(positive)==1, 'Expected one explicit positive confirmation button'
m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',positive[0].get('bounds',''))
assert m, 'Missing confirmation button bounds'
x1,y1,x2,y2=map(int,m.groups())
print((x1+x2)//2,(y1+y2)//2)
PY
)
read -r confirm_x confirm_y <<< "$confirm_tap"
echo "EMULATOR_TRAVEL_CONFIRM_POSITIVE_TARGET=($confirm_x,$confirm_y)"
adb shell input tap "$confirm_x" "$confirm_y"
sleep 3
adb shell run-as com.ailivingworld.mobile cat "$save_dir/state.json" > "$RUNNER_TEMP/alw-state-after-travel.json"
python - <<'PY'
import json, os
from pathlib import Path
state=json.loads((Path(os.environ['RUNNER_TEMP'])/'alw-state-after-travel.json').read_text(encoding='utf-8'))
assert state['player']['location']=='BRENA-CHIEF-HOUSE', 'Confirmed travel did not persist the destination'
assert state['npcs']['BRENA-RANA']['location']=='BRENA-CHIEF-HOUSE', 'Rana location changed unexpectedly'
print('EMULATOR_CONFIRMED_RANA_COLOCATION=PASS')
PY
adb shell screencap -p /sdcard/alw-rana-colocation.png
adb pull /sdcard/alw-rana-colocation.png "$RUNNER_TEMP/alw-rana-colocation.png" > /dev/null
echo "EMULATOR_RANA_COLOCATION_CAPTURE=PASS (button visibility requires screenshot review)"
# Close the expanded travel menu so the colocated NPC action is not obscured.
adb shell input tap 120 120
sleep 1
adb shell uiautomator dump /sdcard/alw-rana-observation.xml > /dev/null
adb shell cat /sdcard/alw-rana-observation.xml > "$RUNNER_TEMP/alw-rana-observation.xml"
python - <<'PY'
import os
from pathlib import Path
from xml.etree import ElementTree as ET
root=ET.parse(Path(os.environ['RUNNER_TEMP'])/'alw-rana-observation.xml').getroot()
texts=[node.get('text','') for node in root.iter() if node.get('text')]
assert '라나 살펴보기' in texts, 'Rana observation action missing after confirmed colocation: '+repr(texts[:35])
print('EMULATOR_RANA_OBSERVATION_ACTION_VISIBLE=PASS')
PY
adb shell screencap -p /sdcard/alw-rana-observation.png
adb pull /sdcard/alw-rana-observation.png "$RUNNER_TEMP/alw-rana-observation.png" > /dev/null


# Observation must be a read-only view, never a player action or world tick.
cp "$RUNNER_TEMP/alw-state-after-travel.json" "$RUNNER_TEMP/alw-state-before-observation.json"
observe_tap=$(python - <<'PY'
import os, re
from pathlib import Path
from xml.etree import ElementTree as ET
root=ET.parse(Path(os.environ['RUNNER_TEMP'])/'alw-rana-observation.xml').getroot()
matches=[n for n in root.iter() if n.get('text','').strip()=='라나 살펴보기']
assert len(matches)==1, 'Expected exactly one Rana observation button'
m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',matches[0].get('bounds',''))
assert m, 'Missing Rana observation button bounds'
x1,y1,x2,y2=map(int,m.groups())
assert x2>x1 and y2>y1
print((x1+x2)//2,(y1+y2)//2)
PY
)
read -r observe_x observe_y <<< "$observe_tap"
adb shell input tap "$observe_x" "$observe_y"
sleep 1
adb shell uiautomator dump /sdcard/alw-rana-observation-result.xml > /dev/null
adb shell cat /sdcard/alw-rana-observation-result.xml > "$RUNNER_TEMP/alw-rana-observation-result.xml"
python - <<'PY'
import os
from pathlib import Path
from xml.etree import ElementTree as ET
root=ET.parse(Path(os.environ['RUNNER_TEMP'])/'alw-rana-observation-result.xml').getroot()
texts=[n.get('text','') for n in root.iter() if n.get('text')]
assert any('라나 · ' in t for t in texts), 'Rana observation details did not appear: '+repr(texts[:35])
print('EMULATOR_RANA_OBSERVATION_DETAILS_VISIBLE=PASS')
PY
adb shell run-as com.ailivingworld.mobile cat "$save_dir/state.json" > "$RUNNER_TEMP/alw-state-after-observation.json"
python - <<'PY'
import json,os
from pathlib import Path
p=Path(os.environ['RUNNER_TEMP'])
before=json.loads((p/'alw-state-before-observation.json').read_text())
after=json.loads((p/'alw-state-after-observation.json').read_text())
assert before==after, 'Read-only Rana observation mutated persisted world state'
print('EMULATOR_RANA_OBSERVATION_READ_ONLY=PASS')
PY
# Capture a fresh final frame over adb. A failed transfer must not invalidate
# the successful state check or leave an old screenshot marked as current.
screenshot="$RUNNER_TEMP/alw-rana-observation-result.png"
for attempt in 1 2 3; do
  if adb exec-out screencap -p > "$screenshot.pending" &&
     python -c 'import sys; from pathlib import Path; data=Path(sys.argv[1]).read_bytes(); sys.exit(0 if data.startswith(bytes.fromhex("89504e470d0a1a0a")) and data.endswith(bytes.fromhex("0000000049454e44ae426082")) else 1)' "$screenshot.pending"; then
    mv "$screenshot.pending" "$screenshot"
    break
  fi
  echo "::warning::Final Android screenshot capture failed on attempt $attempt"
  if [[ "$attempt" == 3 ]]; then exit 1; fi
  sleep 2
done

echo "EMULATOR_BOOT_SMOKE=PASS"
