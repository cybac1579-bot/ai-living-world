"""Activate Brena only for a new Android save; retain existing EventStore journals.

Patch is deliberately anchored to the inspected original Android source.
The original demo asset is retained for compatibility and diagnostics.
"""
from pathlib import Path
import sys

def patch(root: Path) -> None:
    java = root / "android_native/app/src/main/java/com/ailivingworld/mobile/MainActivity.java"
    mobile = root / "android_native/app/src/main/python/mobile_embedded.py"
    j = java.read_text(encoding="utf-8")
    p = mobile.read_text(encoding="utf-8")
    old_j = '"examples/live_demo_world.json"};'
    new_j = '"examples/live_demo_world.json","examples/brena_initial_world.json"};'
    old_p = "    demo = root / 'examples' / 'live_demo_world.json'"
    new_p = """    demo = root / 'examples' / 'live_demo_world.json'
    brena = root / 'examples' / 'brena_initial_world.json'"""
    old_expected = "    expected = [demo, web / 'index.html'"
    new_expected = "    expected = [demo, brena, web / 'index.html'"
    old_return = "    return private, demo, web"
    new_return = "    return private, brena, web"
    for original, replacement in ((old_j,new_j),):
        if j.count(original) != 1:
            raise AssertionError(f"Android asset list anchor mismatch: {original}")
        j = j.replace(original,replacement,1)
    for original,replacement in ((old_p,new_p),(old_expected,new_expected),(old_return,new_return)):
        if p.count(original) != 1:
            raise AssertionError(f"Embedded startup anchor mismatch: {original}")
        p = p.replace(original,replacement,1)
    asset = root / "android_native/app/src/main/assets/examples/brena_initial_world.json"
    if not asset.is_file():
        raise FileNotFoundError("Brena packaged initial world must be staged first")
    java.write_text(j,encoding="utf-8")
    mobile.write_text(p,encoding="utf-8")
    print("BRENA_ANDROID_FIRST_RUN_WIRING=PASS (existing EventStore directory unchanged)")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: patch_brena_android_first_run.py <extracted source>")
    patch(Path(sys.argv[1]))
