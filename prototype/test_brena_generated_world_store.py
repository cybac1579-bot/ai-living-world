"""Regression for the real Android engine with a generated Brena initial state."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from world_engine import EventStore, validate_state
except ModuleNotFoundError:
    EventStore = None


@unittest.skipIf(EventStore is None, "Android source not extracted")
class GeneratedBrenaStoreTests(unittest.TestCase):
    def test_generated_world_survives_eventstore_restart(self):
        import world_engine
        repo = Path(__file__).resolve().parents[1]
        root = Path(world_engine.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "brena.json"
            subprocess.run(
                [sys.executable, str(repo / "tools" / "build_brena_initial_world.py"), str(root), str(output)],
                check=True, capture_output=True, text=True,
            )
            initial = json.loads(output.read_text(encoding="utf-8"))
            validate_state(initial)
            self.assertEqual(len(initial["regions"]), 6)
            self.assertEqual(len(initial["npcs"]), 7)
            self.assertEqual(initial["player"]["location"], "BRENA-SQUARE")
            self.assertEqual(initial["npcs"]["BRENA-RANA"]["location"], "BRENA-CHIEF-HOUSE")
            store_dir = Path(tmp) / "save"
            store = EventStore(store_dir)
            store.create(initial)
            first = store.load()
            self.assertEqual(first, initial)
            # Reading and reopening cannot advance the in-game clock or invent actions.
            cache = store_dir / "state.json"
            if cache.exists():
                cache.unlink()
            restored = EventStore(store_dir).load()
            self.assertEqual(restored, initial)
            self.assertEqual(restored["player"], initial["player"])
            self.assertEqual(restored["npcs"], initial["npcs"])


if __name__ == "__main__":
    unittest.main()
