# Android emulator CI: artifact quota and boot timeout (2026-11-23)

## Verified evidence
- Examined run https://github.com/cybac1579-bot/ai-living-world/actions/runs/45071336100, job 137358740164.
- Offline x86_64 APK compilation: **PASS**.
- Android 15 emulator boot: **FAIL**, timeout waiting for emulator to boot; adb connection to emulator-5554 was refused. This does **not** prove the app itself crashed.
- Host-side diagnostic collection: **PASS**.
- Artifact upload: **FAIL**, GitHub reported `Failed to CreateArtifact: Artifact storage quota has been hit. Unable to upload any new artifacts. Usage is recalculated every 6-12 hours.` This is a **separate quota blocker**, not a diagnostic script syntax failure.
- Visual screenshot and actual rendered scene: **NOT VERIFIED**. Real GPT/Android online login remains disabled.

## Safe change
- In `.github/workflows/android-runtime-emulator.yml`, mark only the upload-artifact step `continue-on-error: true`. The boot step remains mandatory and fails the job on timeout. Existing host diagnostic output in the job log and step summary remains accessible when artifact storage is exhausted.
- No account/authentication/API key changes. No other repository modified.

## Validation and limitations
- Re-read workflow from GitHub after commit to check that only artifact upload is non-blocking; build/boot remains strict.
- This is a workflow-only change; a new GitHub Actions run must confirm runtime behavior. No claim of emulator recovery or completed 20–30 minute AI play loop.
- Artifact quota recovery is controlled by GitHub account storage; avoid repeated upload attempts as a substitute for addressing boot reliability.

## Next steps
1. Check the next CI run: build result, emulator timeout, summary, and whether upload is neutral when quota is exhausted.
2. Investigate emulator process exit/adb refusal from host diagnostics; if CI environment remains flaky, run independent static/unit tests and Android presentation/save-state checks.
3. Keep online login/GPT disabled until authentication and cryptographic security are independently validated and approved.
4. First AI playable remains an estimated **~40%**, not an acceptance-tested completion. Remaining major categories: 6 (runtime, portrait UX/save, auth/GPT, NPC agency/memory, incident slice, device long-run testing).
