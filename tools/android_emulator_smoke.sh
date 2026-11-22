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
for line in texts:
    print(line[:350])
assert any('진단 D4' in t for t in texts), 'Native diagnostic banner not visible: app may have crashed or screen is blank'
assert not any('오류 단계' in t or 'WebView 오류' in t for t in texts), 'The app reports a Python/server/WebView startup error'
assert any('단계 5' in t for t in texts), 'Local WebView page did not finish loading'
print('EMULATOR_NATIVE_UI_AND_LOCAL_PAGE=PASS')
PY

if grep -Eq "FATAL EXCEPTION|Process: com\\.ailivingworld\\.mobile" "$RUNNER_TEMP/alw-startup-log.txt"; then
  echo "::error::Android app process crashed"
  exit 1
fi
adb shell screencap -p /sdcard/alw-screen.png
adb pull /sdcard/alw-screen.png "$RUNNER_TEMP/alw-screen.png" > /dev/null
echo "EMULATOR_BOOT_SMOKE=PASS"
