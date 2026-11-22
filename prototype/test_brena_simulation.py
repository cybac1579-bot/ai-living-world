"""Regression tests for the standalone Brena simulation prototype."""
import unittest

from brena_simulation import BrenaWorld, ACTIVITIES, PLACES


class BrenaSimulationTests(unittest.TestCase):
    def test_no_automatic_time_progression(self):
        world = BrenaWorld.new()
        original = world.to_json()
        self.assertEqual(original, world.to_json())
        self.assertEqual(original, BrenaWorld.from_json(original).to_json())
        world.advance_time(0)
        self.assertEqual(original, world.to_json())

    def test_time_crosses_midnight(self):
        world = BrenaWorld.new()
        world.advance_time(16 * 60 + 20)
        self.assertEqual((world.day, world.minute), (2, 20))

    def test_npc_activity_without_player_action(self):
        world = BrenaWorld.new()
        world.advance_time(60)
        self.assertIn(world.residents["rana"].activity, ACTIVITIES)
        self.assertIn(world.residents["rana"].place, PLACES)
        self.assertEqual(world.residents["smith"].place, "smithy")

    def test_memory_and_relations_survive_save(self):
        world = BrenaWorld.new()
        world.record_event("rana", "resident_a", "promised to help")
        world.set_relation("player", "rana", trust=2)
        world.set_relation("player", "other_adult", affection=1)
        world.set_relation("rana", "other_adult", trust=0)
        loaded = BrenaWorld.from_json(world.to_json())
        self.assertEqual(world.to_json(), loaded.to_json())
        self.assertEqual(loaded.residents["rana"].memories, ["promised to help"])
        self.assertEqual(len(loaded.relations["player"]), 2)

    def test_deterministic_replay_and_no_forced_meeting(self):
        a, b = BrenaWorld.new(seed=4), BrenaWorld.new(seed=4)
        for world in (a, b):
            world.advance_time(60 * 24 * 7, rainy=True)
        self.assertEqual(a.to_json(), b.to_json())
        self.assertFalse(any("player" in str(event) for event in a.events))

    def test_reject_invalid_time(self):
        world = BrenaWorld.new()
        for value in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                world.advance_time(value)


if __name__ == "__main__":
    unittest.main()
