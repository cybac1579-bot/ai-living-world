"""Stage a user-approved Rana portrait in both original Android VN asset trees.

Explicit input only. The CI never fabricates an image or downloads one.
"""
from pathlib import Path
import argparse
import shutil

DESTINATION = Path("assets/characters/rana/neutral.webp")

def stage(root: Path, portrait: Path) -> list[Path]:
    if portrait.suffix.lower() != ".webp" or not portrait.is_file():
        raise ValueError("An existing approved WebP portrait is required")
    payload = portrait.read_bytes()
    if len(payload) > 5 * 1024 * 1024:
        raise ValueError("Approved portrait exceeds the 5 MiB mobile budget")
    if len(payload) < 20 or not payload.startswith(b"RIFF") or payload[8:12] != b"WEBP":
        raise ValueError("Invalid WebP file")
    parents = [root / "web", root / "android_native/app/src/main/assets/web"]
    existing = [p for p in parents if (p / "app.js").is_file()]
    if not existing:
        raise FileNotFoundError("Original VN web assets missing")
    outputs = []
    for parent in existing:
        target = parent / DESTINATION
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != payload:
            raise FileExistsError(f"Refusing to replace existing Rana portrait: {target}")
        if not target.exists():
            shutil.copyfile(portrait, target)
        outputs.append(target)
    return outputs

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("android_src",type=Path)
    parser.add_argument("--approved-rana-portrait",required=True,type=Path)
    args=parser.parse_args()
    for output in stage(args.android_src,args.approved_rana_portrait):
        print("STAGED_RANA_PORTRAIT",output)
