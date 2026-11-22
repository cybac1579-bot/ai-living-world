# Android emulator failure-evidence step hardening — 2026-11-23

## Observed before change
- main was `7c7f9e6375afa68b69f99b21377c83c013fa62a2`.
- [Run 45059039800](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45059039800) completed with failure. The x86_64 debug APK compilation step passed, the emulator boot step failed, and **the new host-side evidence collection step also failed**. Artifact upload step completed, but whether any useful artifact files were uploaded is not established by its step conclusion.
- Earlier [run 45048239566](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45048239566) succeeded; this intermittent behavior cannot be attributed to the app without emulator logs.
- Open issue #1 remains unresolved.

## Change made
- Updated `.github/workflows/android-runtime-emulator.yml` only.
- Replaced fragile escaped-parenthesis `find` expression with two simple filename searches. The prior shell line contained double backslashes before the parentheses and could be parsed as an invalid shell expression; this is a **suspected**, not log-proven, cause of the evidence-step failure.
- Explicitly allow missing adb/KVM/processes and ensure the diagnostic step exits successfully after writing its file. The actual emulator test still fails when boot fails; only the auxiliary diagnostic collector is made non-blocking.
- Keep the offline-only APK variant, disabled login/GPT controls, and short-lived diagnostic artifact retention unchanged.

## Verification and limits
- Reviewed GitHub Actions job-step conclusions for run 45059039800 and fetched the exact previous workflow text before the SHA-guarded update.
- This is a workflow-only change; no application code or APK behavior changed. GitHub Actions must still execute the new commit before the collector can be called working.
- No emulator screenshot was inspected. Successful compilation and WebView pageFinished are not proof of a rendered VN scene or functioning GPT conversation.

## Next
1. Inspect the workflow run triggered by this commit. Verify the evidence step completes and a readable `alw-emulator-host-diagnostics.txt` is available when boot fails.
2. If emulator boots, review screenshot for forest and speaker dialogue, and verify portrait presentation.
3. Continue save/restore, authorization/security review, NPC free-input/causal-memory loop, 20–30 minute multi-NPC incident, and real-device endurance testing.

## Progress estimate
Keep **~40% rough planning estimate** unchanged. Six broad areas remain: Android runtime/visual reliability, portrait UI/save, secure GPT, NPC choice/memory, vertical-slice content, and device endurance.
