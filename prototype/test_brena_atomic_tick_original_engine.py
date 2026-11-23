"""Verify Brena's atomic clock/NPC transition against original EventStore.

Runs only when the extracted, patched Android engine is on PYTHONPATH.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from world_engine import EventStore, validate_state
except ModuleNotFoundError:
    EventStore = None


@unittest.skipIf(EventStore is None, "original engine not staged")
class BrenaAtomicWorldTickTests(unittest.TestCase):
    def test_clock_npc_and_replay_use_one_journal_revision(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            sample = Path(temp) / "brena.json"
            subprocess.run([sys.executable, str(root / "tools/build_brena_initial_world.py"),
                            str(root / "src"), str(sample)], check=True, capture_output=True)
            initial = json.loads(sample.read_text(encoding="utf-8"))
            validate_state(initial)
            store = EventStore(Path(temp) / "save")
            store.create(initial)
            old_player = initial["player"]["location"]
            old_npcs = {k: v["location"] for k, v in initial["npcs"].items()}
            for revision in range(6):
                state = store.commit(revision, None,
                    {"events": [{"type": "world_advance", "minutes": 10}]},
                    mode="brena_world_tick")
                self.assertEqual(state["revision"], revision + 1)
                self.assertEqual(state["world_minutes"], initial["world_minutes"] + (revision + 1) * 10)
                self.assertEqual(state["player"]["location"], old_player)
                for npc, info in state["npcs"].items():
                    self.assertIn(info["location"], state["regions"])
            self.assertTrue(any(state["npcs"][k]["location"] != v for k, v in old_npcs.items())
                            or state["world_minutes"] > initial["world_minutes"])
            cache = Path(temp) / "save/state.json"
            if cache.exists():
                cache.unlink()
            self.assertEqual(EventStore(Path(temp) / "save").load(), state)
            with self.assertRaises(Exception):
                store.commit(5, None, {"events": [{"type": "world_advance", "minutes": 10}]},
                             mode="brena_world_tick")


if __name__ == "__main__":
    unittest.main()
