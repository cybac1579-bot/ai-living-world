"""Stage Brena modules inside the extracted Android Python source tree.

Does not overwrite original engine, Android UI, or existing user saves.
This is a packaging prerequisite, not a claim that the UI invokes Brena.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

MODULES = (
    "brena_simulation.py",
    "brena_dialogue_context.py",
    "brena_android_boundary.py",
    "brena_event_adapter.py",
    "brena_clock_projection.py",
    "brena_engine_clock_bridge.py",
    "brena_presentation_payload.py",
)


def stage(prototype: Path, android_src: Path) -> list[Path]:
    if not (android_src / "world_engine.py").is_file():
        raise FileNotFoundError("original world_engine.py must exist in Android source")
    outputs = []
    for name in MODULES:
        origin = prototype / name
        target = android_src / name
        if not origin.is_file():
            raise FileNotFoundError(origin)
        if target.exists():
            if target.read_bytes() != origin.read_bytes():
                raise FileExistsError(f"refusing to overwrite existing Android module: {name}")
        else:
            shutil.copyfile(origin, target)
        outputs.append(target)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("android_src", type=Path)
    parser.add_argument("--prototype", type=Path, default=Path("prototype"))
    args = parser.parse_args()
    for path in stage(args.prototype, args.android_src):
        print("STAGED", path)


if __name__ == "__main__":
    main()
