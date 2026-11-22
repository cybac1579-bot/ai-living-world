# Android emulator intermittent boot failure and host evidence — 2026-11-23

## Verified state
- Baseline main before this work: `175d1d789ed2128440ea33afc8d010232def14b9`.
- Run [45048239566](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45048239566) **passed** the Android 15 emulator boot and local WebView pageFinished smoke. This does not prove correct visual scene rendering.
- Later run [45053371342](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45053371342) **failed** despite successful x86_64 APK compilation. Job `137303172965` reported `adb: device 'emulator-5554' not found` repeatedly and `Timeout waiting for emulator to boot` after 900 seconds. The smoke script never ran, and the artifact uploader reported no files. Do not call this an app runtime regression without further evidence.
- Open issue #1 still tracks Android/GPT/real-device validation.

## Change this run
- Updated `.github/workflows/android-runtime-emulator.yml` to execute a failure-only, host-side diagnostic step *before* artifact upload. It writes `$RUNNER_TEMP/alw-emulator-host-diagnostics.txt` with UTC timestamp, adb device list, KVM access, memory, disk, emulator/adb processes, and candidate emulator logs.
- Added that file to the existing artifact upload paths. It must work even when the emulator never reaches adb or the smoke script never executes.
- No authentication, GPT, API keys, user data, or other repositories were changed.

## Verification / limitations
- Confirmed the failure from GitHub job steps and decoded job logs, not inferred from the previous report.
- YAML edit was committed via GitHub with an exact blob SHA, preserving concurrent changes.
- The new workflow run must be inspected before claiming the diagnostic artifact works; a GitHub contents update is not an Android build or emulator execution.
- Even on a future green run, screenshot inspection and real-device long-play remain outstanding.

## Next
1. Inspect the new workflow run and its artifact. If the emulator boot fails again, compare host diagnostics to the earlier successful run; if it succeeds, inspect captured PNG for actual forest scene and dialogue.
2. Keep offline-only emulator variant and disabled Android login/GPT buttons until separate authentication/security approval and verification.
3. Continue portrait VN UI and persistent NPC/choice test coverage without conflating successful APK compilation with a 20–30 minute AI playthrough.

## First AI playable progress
Retain conservative **~40% rough planning estimate**, not measured completion. Six broad remaining areas: reliable Android visual/runtime tests; portrait UX and save/restore; safe authentication/GPT; NPC memory/choice/free input; 20–30 minute multi-NPC incident slice; device endurance testing.
