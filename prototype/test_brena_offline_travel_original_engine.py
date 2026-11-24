"""Real original-engine travel persistence and journal replay regression."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

try:
    import world_engine
    from world_engine import EventStore, validate_state
except ModuleNotFoundError:
    world_engine = None

@unittest.skipIf(world_engine is None, "original Android engine not unpacked")
class OfflineTravelOriginalEngineTests(unittest.TestCase):
    def test_explicit_travel_replays_without_gpt_or_time_change(self):
        # Reuse the existing six-place Brena fixture generator, which derives
        # its schema from the original live_demo_world.json.
        import subprocess
        import sys
        engine_dir=Path(world_engine.__file__).resolve().parent
        repo=Path(__file__).resolve().parents[1]
        source_root=repo/"src"
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"brena.json"
            subprocess.run([sys.executable,str(repo/"tools"/"build_brena_initial_world.py"),
                            str(source_root),str(output)],check=True,capture_output=True,text=True)
            state=json.loads(output.read_text(encoding="utf-8"))
        validate_state(state)
        self.assertEqual(state["player"]["location"],"BRENA-SQUARE")
        origin=state["player"]["location"]
        destination=state["regions"][origin]["neighbors"][0]
        before_clock={k:state.get(k) for k in ("world_minutes","world_time","day","minute")}
        with tempfile.TemporaryDirectory() as directory:
            store=EventStore(Path(directory))
            store.create(state)
            after=store.commit(0,{"destination":destination},{"events":[]},mode="player_travel")
            self.assertEqual(after["player"]["location"],destination)
            self.assertEqual(after["revision"],1)
            self.assertEqual({k:after.get(k) for k in before_clock},before_clock)
            with self.assertRaises(Exception):
                store.commit(0,{"destination":origin},{"events":[]},mode="player_travel")
            if (Path(directory)/"state.json").exists():
                (Path(directory)/"state.json").unlink()
            replay=EventStore(Path(directory)).load()
            self.assertEqual(after,replay)
            with self.assertRaises(Exception):
                EventStore(Path(directory)).commit(1,{"destination":"unregistered_place"},{"events":[]},mode="player_travel")
            # Return to the square using a fresh store instance, then force
            # a second journal replay. A one-way move is not enough.
            returned=EventStore(Path(directory)).commit(
                1,{"destination":origin},{"events":[]},mode="player_travel")
            self.assertEqual(returned["player"]["location"],origin)
            self.assertEqual(returned["revision"],2)
            self.assertEqual({k:returned.get(k) for k in before_clock},before_clock)
            if (Path(directory)/"state.json").exists():
                (Path(directory)/"state.json").unlink()
            self.assertEqual(EventStore(Path(directory)).load(),returned)

if __name__=="__main__":
    unittest.main()
