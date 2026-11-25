#!/usr/bin/env bash
set -euo pipefail
package=com.ailivingworld.mobile.plancheck
adb install -r plan-check/app/build/outputs/apk/release/app-release.apk
adb logcat -c
adb shell am start -W -n "$package/com.ailivingworld.mobile.MainActivity"
for attempt in {1..45}; do
    markers=$(adb logcat -d -s ALW_PLAN_CHECK:I)
    if [[ "$markers" == *ANDROID_SIGNED_IDENTITY_PASS* && "$markers" == *ANDROID_LOGIN_BROWSER_HANDOFF_PASS* ]]; then
        echo "ANDROID_SIGNED_IDENTITY_PASS ANDROID_LOGIN_BROWSER_HANDOFF_PASS"
        adb shell am force-stop "$package"
        exit 0
    fi
    sleep 2
done
echo "::error::Android identity verification or login-button browser handoff did not complete"
exit 1
