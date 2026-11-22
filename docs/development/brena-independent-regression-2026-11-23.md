# Brena independent CI regression — 2026-11-23

## Why
Android emulator boot intermittently fails before app startup, and GitHub artifact storage is over quota. Neither condition should prevent testing the standalone NPC/time/memory/save logic. This workflow is deliberately independent of the Android emulator and artifact uploads.

## Implemented
- `.github/workflows/brena-prototype-regression.yml`
- Triggers on changes to `prototype/**` or the workflow itself, pull requests, and manual dispatch.
- Python 3.11 compileall; unittest discovery for prototype tests; additional 72-hour deterministic replay, save/load equivalence, dialogue context equivalence, and no invented player event assertion.
- 10-minute timeout; read-only GitHub permissions; no credentials, GPT calls, or Android build.

## Verification status
- Workflow file committed to main; tests are **not claimed PASS until the corresponding GitHub Actions run reports success**.
- This tests only the isolated Brena prototype; it does **not** prove Android UI, NPC dialogue integration, GPT login, real gameplay, or device saves.
- Android emulator workflow remains separate and mandatory for Android runtime acceptance.
- This step changes no game lore, NPC identities, user decisions, or authentication boundaries.

## Next
1. Inspect first workflow run and repair any failing test.
2. Continue Android emulator diagnosis in parallel, but prioritize connecting the world prototype to actual Android save/time/dialogue paths.
3. Track the 20–30 minute AI play-loop acceptance separately from offline unit tests.

Progress estimate unchanged (~40%, unverified estimate). Six major acceptance categories remain.
