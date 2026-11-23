"""Original EventStore replay must preserve the read-only Rana VN status.

Runs against the real extracted Android engine and its validated fixture.
"""
import json
import tempfile
import unittest
from pathlib import Path

from brena_presentation_payload import rana_status_payload
try:
    import world_engine
    from world_engine import EventStore, validate_state
except ModuleNotFoundError:
    world_engine = None


@unittest.skipIf(world_engine is None, "Original Android engine not extracted")
class RanaOriginalStoreReplayTests(unittest.TestCase):
    def test_real_store_reload_and_cache_rebuild_keep_rana_status(self):
        fixtures = Path(world_engine.__file__).resolve().parent / "examples"
        initial = None
        for p in sorted(fixtures.glob("*.json")):
            try:
                candidate = json.loads(p.read_text(encoding="utf-8"))
                validate_state(candidate)
                if candidate["revision"] == 0 and type(candidate.get("world_minutes")) is int:
                    initial = candidate
                    break
            except (ValueError, TypeError, KeyError):
                continue
        self.assertIsNotNone(initial, "No validated original fixture with world_minutes")
        with tempfile.TemporaryDirectory() as temp:
            store = EventStore(Path(temp))
            store.create(initial)
            saved = store.load()
            baseline = rana_status_payload(saved)
            self.assertEqual(saved, initial)
            self.assertEqual(rana_status_payload(store.load()), baseline)
            # Simulate process restart with a fresh EventStore instance.
            self.assertEqual(rana_status_payload(EventStore(Path(temp)).load()), baseline)
            # Remove derived cache: replay authoritative event journal instead.
            cache = Path(temp) / "state.json"
            if cache.exists():
                cache.unlink()
            replayed = EventStore(Path(temp)).load()
            self.assertEqual(replayed, saved)
            self.assertEqual(rana_status_payload(replayed), baseline)
            self.assertEqual(replayed["player"], initial["player"])
            self.assertNotIn("dialogue", baseline)
            self.assertNotIn("player_action", baseline)


if __name__ == "__main__":
    unittest.main()
