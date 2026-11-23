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
        engine_dir=Path(world_engine.__file__).resolve().parent
        examples=engine_dir / "examples"
        if not list(examples.glob("*.json")):
            examples=engine_dir.parent.parent.parent.parent / "examples"
        print("TRAVEL_FIXTURE_DISCOVERY",str(examples),[p.name for p in examples.glob("*.json")])
        state=None
        for file in sorted(examples.glob("*.json")):
            try:
                candidate=json.loads(file.read_text(encoding="utf-8"))
                validate_state(candidate)
                current=candidate["player"]["location"]
                if candidate["revision"]==0:
                    for region_id,region in candidate["regions"].items():
                        if region.get("neighbors"):
                            candidate["player"]["location"]=region_id
                            validate_state(candidate)
                            state=candidate
                            break
                    if state is not None:
                        break
            except (ValueError,KeyError,TypeError):
                pass
        if state is None:
            # TEST-ONLY geography: connect two existing regions, never alter game data.
            for file in sorted(examples.glob("*.json")):
                try:
                    candidate=json.loads(file.read_text(encoding="utf-8"))
                    validate_state(candidate)
                    ids=list(candidate["regions"])
                    if candidate["revision"] != 0 or len(ids)<2:
                        continue
                    origin_id,destination_id=ids[:2]
                    candidate["player"]["location"]=origin_id
                    candidate["regions"][origin_id]["neighbors"]=[destination_id]
                    candidate["regions"][destination_id]["neighbors"]=[origin_id]
                    validate_state(candidate)
                    state=candidate
                    print("OFFLINE_TRAVEL_TEST_FIXTURE=synthetic_adjacency_existing_regions")
                    break
                except (ValueError,KeyError,TypeError):
                    continue
        self.assertIsNotNone(state,"Original fixtures lack two valid regions; cannot prove offline travel")
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

if __name__=="__main__":
    unittest.main()
