#!/usr/bin/env bash
set -euo pipefail
package=com.ailivingworld.mobile.plancheck
adb install -r plan-check/app/build/outputs/apk/release/app-release.apk
adb logcat -c
adb shell am start -W -n "$package/com.ailivingworld.mobile.MainActivity"
for attempt in {1..45}; do
    if adb logcat -d -s ALW_PLAN_CHECK:I | grep -F ANDROID_SIGNED_IDENTITY_PASS; then
        adb shell am force-stop "$package"
        exit 0
    fi
    sleep 2
done
echo "::error::Android did not verify the signed identity fixture and reject the mismatched nonce"
exit 1
