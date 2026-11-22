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
    packaged_python = android_src / "android_native/app/src/main/python"
    if not (packaged_python / "world_engine.py").is_file():
        raise FileNotFoundError("Chaquopy packaged Python source must contain world_engine.py")
    outputs = []
    for name in MODULES:
        origin = prototype / name
        if not origin.is_file():
            raise FileNotFoundError(origin)
        # Root copy supports original-engine tests; nested copy is packaged by
        # Chaquopy into the actual Android APK.
        for directory in (android_src, packaged_python):
            target = directory / name
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
