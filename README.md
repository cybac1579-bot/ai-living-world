# AI Living World 🎮

AI Living World is a private, experimental living-world visual novel / RPG prototype.

## Build status

This repository contains a **development source snapshot**, not a verified or release-ready Android app. The first CI goal is to compile an **offline-only debug APK** for interface and local-save testing. ChatGPT login and online model calls **must remain disabled** in that debug APK until the Android authentication and cryptography security work is independently verified.

- Source baseline: v1.3 (world engine, visual novel interface, Android/Chaquopy project)
- Previous Windows SIWC/real-GPT test: successful on the user's PC; not Android-verified
- Android device installation / OAuth / gameplay: not yet verified
- Never commit OAuth tokens, `credentials.json`, save data, signing keys or user account secrets.

## Source package

`source/AI_Living_World_Android_v1.3.zip` is a checked-in source snapshot. The Android CI workflow extracts it inside the GitHub Actions runner, runs offline tests, and attempts the Android debug build. The package is **not** an APK. The source snapshot is retained until the project is unpacked into version-controlled files in a subsequent development step.

Canonical development archive and verification logs are backed up in the owner's private Google Drive.

## First real Android CI result (2026-11-22)

**Cloud Android build: PASS.** The GitHub runner executed all 238 Python regression tests, installed Android SDK 36 and Gradle 9.6, compiled a Chaquopy/ARM64 debug APK, and verified its archive structure.

- [Successful build log](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45032205761)
- [Private prerelease with offline-only APK](https://github.com/cybac1579-bot/ai-living-world/releases/tag/offline-debug-c0d5c57b5a2f)
- APK: `app-debug.apk` (24,492,028 bytes)
- SHA-256: `fbb8876b7365accdbf1316584863705e6be9e9ddf8d1b871d1a2bd8505077daf`

**Security boundary:** The CI workflow disables the Android login and GPT-play buttons before compilation and omits outdated native cryptography wheels. This APK is an **offline UI / local-save debug prototype only**, not a working ChatGPT login client. A real Galaxy S25+ installation and run have not yet been verified. Do not enter sensitive information into a debug build.

GitHub Actions artifact storage quota was exhausted, so the APK is delivered through a private GitHub prerelease rather than an Actions artifact.

## Galaxy S25+ offline startup fix (2026-11-22)

**Important correction:** The previous offline-only debug build `offline-debug-7c3938d9a072` removed the Android `INTERNET` permission. That permission is still **required to open sockets on 127.0.0.1**, even when the app runs without external online services. On a real device, the app could therefore fail to start its own local interface server and show a generic Android runtime/auth/resource error.

The corrected debug build:
- Keeps `android.permission.INTERNET` for the private loopback HTTP server, and checks that permission in the assembled APK.
- Binds the embedded HTTP engine only to `127.0.0.1` and retains the explicit cleartext exception for that host.
- Keeps ChatGPT login and online GPT controls disabled; offline demo starts without credentials or a token. **Android's INTERNET permission is not a general OS-level outbound-network firewall:** this is an application-level offline-mode restriction.
- Converts native toolbar/status height from raw pixels to density-independent dp and applies Android 15+ safe-area insets to prevent cropped buttons and error text on high-density devices.
- Continues running offline engine regression tests in CI.

[Latest corrected debug APK](https://github.com/cybac1579-bot/ai-living-world/releases/tag/offline-debug-14028108f0e5) | [Build run](https://github.com/cybac1579-bot/ai-living-world/actions/runs/45033924393) | [On-device checklist](docs/android-device-smoke-test-ko.md)

**Status:** compilation and APK permission checks passed in the corrected build. Real Galaxy S25+ startup and save behavior still need device verification. Do not enter credentials or sensitive information into this prototype. The original v1.3 ZIP remains a baseline; debug-only patches are applied to an unpacked CI working copy.
