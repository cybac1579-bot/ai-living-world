"""Persistence regressions: backup, crash recovery, and no offline time skip."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brena_simulation import BrenaWorld
from brena_save import load_world, save_world


class SaveTests(unittest.TestCase):
    def test_roundtrip_and_no_time_progression(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            world = BrenaWorld.new(seed=9)
            world.advance_time(120)
            save_world(path, world)
            self.assertEqual(load_world(path).to_json(), world.to_json())

    def test_corrupt_primary_recovers_previous_valid_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            previous = BrenaWorld.new()
            save_world(path, previous)
            current = BrenaWorld.from_json(previous.to_json())
            current.advance_time(60)
            save_world(path, current)
            path.write_text("{corrupt", encoding="utf-8")
            self.assertEqual(load_world(path).to_json(), previous.to_json())

    def test_interrupted_replace_keeps_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            previous = BrenaWorld.new()
            save_world(path, previous)
            newer = BrenaWorld.new(seed=2)
            with patch("brena_save.os.replace", side_effect=OSError("simulated crash")):
                with self.assertRaises(OSError):
                    save_world(path, newer)
            self.assertEqual(load_world(path).to_json(), previous.to_json())
            self.assertFalse(list(Path(directory).glob(".alw-*.tmp")))

    def test_bad_primary_does_not_overwrite_good_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            first = BrenaWorld.new(seed=1)
            save_world(path, first)
            save_world(path, BrenaWorld.new(seed=2))
            path.write_text("invalid", encoding="utf-8")
            save_world(path, BrenaWorld.new(seed=3))
            self.assertEqual(load_world(path).seed, 3)
            self.assertEqual(load_world(path.with_name("world.json.bak")).seed, 1)

    def test_structurally_invalid_primary_falls_back_to_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            previous = BrenaWorld.new(seed=10)
            save_world(path, previous)
            save_world(path, BrenaWorld.new(seed=11))
            corrupted = json.loads(path.read_text(encoding="utf-8"))
            corrupted["residents"]["rana"]["place"] = "nonexistent_location"
            path.write_text(json.dumps(corrupted), encoding="utf-8")
            self.assertEqual(load_world(path).seed, 10)

    def test_invalid_snapshot_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            world = BrenaWorld.new()
            world.residents["rana"].place = "unknown"
            with self.assertRaises(ValueError):
                save_world(path, world)
            self.assertFalse(path.exists())

    def test_invalid_event_and_relation_snapshots_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            previous = BrenaWorld.new(seed=17)
            save_world(path, previous)
            save_world(path, BrenaWorld.new(seed=18))
            base = json.loads(path.read_text(encoding="utf-8"))
            bad_cases = [
                {"events": [{"day": True, "minute": 0, "actor": "rana", "subject": "player", "detail": "x"}]},
                {"events": [{"day": 2, "minute": 0, "actor": "rana", "subject": "player", "detail": "x"}]},
                {"events": [{"day": 1, "minute": 0, "actor": "unknown", "subject": "player", "detail": "x"}]},
                {"relations": {"rana": ["player"]}},
                {"relations": {"rana": {"player": "friendly"}}},
                {"relations": {"rana": {"rana": {"trust": 1}}}},
            ]
            for mutation in bad_cases:
                corrupted = dict(base)
                corrupted.update(mutation)
                path.write_text(json.dumps(corrupted), encoding="utf-8")
                self.assertEqual(load_world(path).seed, 17, mutation)

    def test_valid_event_and_relation_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "world.json"
            world = BrenaWorld.new(seed=19)
            world.record_event("rana", "player", "met at square")
            world.set_relation("rana", "player", trust=1)
            save_world(path, world)
            self.assertEqual(load_world(path).to_json(), world.to_json())

    def test_unknown_relation_participant_rejected_at_mutation(self):
        world = BrenaWorld.new()
        with self.assertRaises(ValueError):
            world.set_relation("rana", "unregistered_person", trust=1)
        with self.assertRaises(ValueError):
            world.set_relation("unregistered_person", "player", trust=1)
        self.assertEqual(world.relations, {})

    def test_no_valid_save_is_error_not_silent_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                load_world(Path(directory) / "missing.json")


if __name__ == "__main__":
    unittest.main()
