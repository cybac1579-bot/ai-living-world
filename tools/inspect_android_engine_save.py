"""Report narrow, reviewable Android world-engine integration excerpts.

Only emits local source lines from explicitly named files; no environment values,
keys, or configuration files are read. Used to inspect the original engine
before deciding whether to modify persistence behavior.
"""
from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "src")
ranges = {
    "world_engine.py": ((1, 145), (170, 260), (360, 450), (525, 670)),
    "vn_server.py": ((105, 130), (175, 225)),
}
for filename, spans in ranges.items():
    path = root / filename
    if not path.is_file():
        raise SystemExit(f"Required Android engine file missing: {filename}")
    lines = path.read_text(encoding="utf-8").splitlines()
    print(f"===== {filename} ({len(lines)} lines) =====")
    for start, end in spans:
        print(f"--- lines {start}-{min(end, len(lines))} ---")
        for line_number in range(start, min(end, len(lines)) + 1):
            line = lines[line_number - 1]
            if any(token in line.lower() for token in ("password", "secret", "api_key", "access_token", "authorization", "private_key")):
                print(f"{line_number:4d}: [redacted potentially sensitive line]")
            else:
                print(f"{line_number:4d}: {line[:250]}")
