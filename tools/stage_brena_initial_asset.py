"""Stage a validated Brena initial world as an Android packaged asset.

Does not touch user saves. The original demo asset remains available for
legacy saves and diagnostics; first-run activation is a separate guarded step.
"""
from pathlib import Path
import json
import subprocess
import sys

def stage(root: Path, repo: Path) -> Path:
    root = root.resolve()
    output = root / "android_native/app/src/main/assets/examples/brena_initial_world.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite packaged Brena asset: {output}")
    generator = repo / "tools/build_brena_initial_world.py"
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        generated = Path(tmp) / "brena.json"
        subprocess.run([sys.executable, str(generator), str(root), str(generated)],
                       check=True, capture_output=True, text=True)
        state = json.loads(generated.read_text(encoding="utf-8"))
        assert state["player"]["location"] == "BRENA-SQUARE"
        assert "BRENA-RANA" in state["npcs"]
        with output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    print("BRENA_ANDROID_INITIAL_ASSET=PASS", output)
    return output

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: stage_brena_initial_asset.py <extracted source>")
    stage(Path(sys.argv[1]), Path(__file__).resolve().parents[1])
