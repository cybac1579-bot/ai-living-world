# Android /api/state patch regression — 2026-11-23

## Basis
Read latest main `acb612f7` PROJECT_SOURCE_OF_TRUTH and the linked autonomous world, Brena, Rana, first-playable, long-term relationship, and relationship architecture documents. No canon changes.

## This change
Added `prototype/test_brena_android_state_patch_contract.py` on PR #2 development branch. It checks the actual `tools/patch_brena_vn_state.py` patcher against a minimal synthetic server source:
- the injected payload reads the engine store once and does not use a client-provided location;
- an unexpected original response anchor raises an error without writing a partially modified file;
- a second application fails rather than duplicating the injection.

This is a **patch contract test**, not a running `/api/state` HTTP test, Android APK build, real-world source ZIP test, or proof that all original engine fields are private. The existing call `rana_status_payload(engine_state)` omits authoritative player location and therefore deliberately hides NPC activity. Do not resolve that by accepting untrusted request location. The clock-projected Brena NPC state is not yet proven identical to the original EventStore's NPC state.

## Next gate
Extract the original Android ZIP and inspect `world_engine.render_contract`, `engine_state["player"]["location"]`, region IDs, `vn_server.py` and all HTTP response paths. Only then implement validated original-engine-to-Brena location mapping and same/different/unknown/spoofed-location API tests, plus EventStore save/replay checks. Keep online login/GPT disabled. No main merge until CI and Android checks are separately reported.

## Verification
GitHub branch commit contains the test and this note. Test execution, CI, original APK build, and Android runtime **not verified in this operation**. No main or other repository changes.
