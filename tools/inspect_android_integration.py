"""Inspect unpacked Android source integration points without modifying source.

Usage: python tools/inspect_android_integration.py src
The report lists candidate files and matching line numbers, not secrets or source text.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "src").resolve()
TOKENS = {
    "save": ("save_game", "save_state", "save_data", "savefile", "json.dump", "write_text", "open("),
    "load": ("load_game", "load_state", "load_data", "json.load", "read_text"),
    "time": ("advance_time", "game_time", "world_time", "time_step"),
    "dialogue": ("dialogue", "chat", "npc_memory", "memory"),
}
SKIP = {".git", ".gradle", "build", "__pycache__", ".idea", "venv", ".venv", "node_modules"}
MAX_FILE_BYTES = 350_000


def inventory(root: Path) -> dict:
    if not root.is_dir():
        raise FileNotFoundError(f"unpacked source not found: {root}")
    matches = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in {".py", ".java", ".kt"}:
            continue
        if SKIP.intersection(path.relative_to(root).parts) or path.stat().st_size > MAX_FILE_BYTES:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        found = {}
        for category, tokens in TOKENS.items():
            numbers = [i for i, line in enumerate(lines, 1) if any(token in line.lower() for token in tokens)]
            if numbers:
                found[category] = numbers[:15]
        if found:
            matches.append({"path": path.relative_to(root).as_posix(), "matches": found})
    return {"source_root": root.name, "candidate_files": matches[:120]}


if __name__ == "__main__":
    print(json.dumps(inventory(ROOT), ensure_ascii=False, indent=2))
