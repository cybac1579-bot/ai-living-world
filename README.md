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
