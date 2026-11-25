#!/usr/bin/env bash
# Maven sometimes rate-limits the first download on a fresh Actions runner.
set -euo pipefail
log=$(mktemp)
trap 'rm -f "$log"' EXIT
for delay in 45 120 0; do
  if gradle -p plan-check "$@" --no-daemon 2>&1 | tee "$log"; then
    exit 0
  else
    status=${PIPESTATUS[0]}
  fi
  if [[ "$status" == 0 || "$delay" == 0 ]] || ! grep -Eiq 'status code 429|HTTP 429|Too Many Requests' "$log"; then
    exit "$((status == 0 ? 1 : status))"
  fi
  echo "::warning::Dependency server returned HTTP 429. Retrying in ${delay}s."
  sleep "$delay"
done
