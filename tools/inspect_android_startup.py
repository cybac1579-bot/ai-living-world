"""Inspect real Android startup and initial-state selection before patching it.

Print bounded source excerpts only; this is discovery, not an activation claim.
"""
from pathlib import Path
import argparse

KEYWORDS = ("live_demo_world", "initial_state", "store.create", "EventStore(",
            "startEngine(", "start_engine(", "vn_server", "world_engine")

def inspect(root: Path) -> int:
    files = (
        root / "vn_server.py",
        root / "android_native/app/src/main/python/mobile_embedded.py",
        root / "android_native/app/src/main/python/vn_server.py",
        root / "android_native/app/src/main/java/com/ailivingworld/mobile/MainActivity.java",
    )
    matches = 0
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(token in line for token in KEYWORDS):
                # No environment, config or token values; only source-level wiring.
                if any(secret in line.lower() for secret in ("password", "secret", "token", "api_key")):
                    continue
                print(f"STARTUP_SOURCE {path.relative_to(root)}:{lineno} {line.strip()[:220]}")
                matches += 1
    # Show bounded nearby source so asset-copy and first-launch behavior can be
    # reviewed before changing which world the app loads.
    for path in files:
        lines = path.read_text(encoding="utf-8").splitlines()
        anchors = [i for i, line in enumerate(lines)
                   if "live_demo_world.json" in line or "SAMPLE =" in line
                   or "EventStore(" in line or "store.create(" in line
                   or "def start_engine" in line or "def start_server" in line
                   or "def _ensure" in line or "def start" in line
                   or "private void startEngine" in line]
        emitted = set()
        for i in anchors:
            for n in range(max(0, i - 5), min(len(lines), i + 9)):
                if n in emitted:
                    continue
                emitted.add(n)
                line = lines[n]
                if any(secret in line.lower() for secret in
                       ("password", "secret", "token", "api_key", "authorization")):
                    continue
                print(f"STARTUP_CONTEXT {path.relative_to(root)}:{n+1} {line[:220]}")
    if not matches:
        raise AssertionError("No Android startup/initial-state anchors found")
    print(f"ANDROID_STARTUP_ANCHORS=PASS {matches}")
    return matches


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    inspect(args.root)
