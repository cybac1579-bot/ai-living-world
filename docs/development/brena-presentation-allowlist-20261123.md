# Brena presentation allowlist gate — 2026-11-23

## Basis
Read latest main acb612f7 PROJECT_SOURCE_OF_TRUTH and all six linked canonical world/Rana/Brena/first-playable/relationship documents. No canon changes. Actions are blocked by account usage/budget policy; no CI run or APK/emulator build was triggered.

## Change
In prototype/brena_presentation_payload.py, unknown projected NPC place/activity identifiers and display labels now return null rather than echoing internal codes to the Android-facing Brena presentation object. Known codes remain unchanged. Added prototype/test_brena_presentation_unknown_labels.py with synthetic unknown/known projection cases.

## Limits
This is a narrow presentation allowlist, **not** proof of full /api/state privacy, authoritative player location, or Android execution. The original server patch still omits player location, so NPC activity may remain hidden even when co-located. The original EventStore and ZIP have not been runtime-tested here. New test was added but **not executed**; CI remains blocked. Main and online auth/GPT unchanged.

## Next gate
When an executable local Python environment with the branch source is available, run the new unittest and existing presentation/state contract regressions without GitHub Actions. Inspect actual Android ZIP's server and world state before any authoritative player-location mapping; validate save/replay and all response paths before merging PR #2.
