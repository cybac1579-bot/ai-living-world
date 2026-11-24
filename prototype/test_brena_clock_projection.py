"""Brena clock projection must be deterministic and never infer offline time."""
import unittest

from brena_simulation import BrenaWorld
from brena_clock_projection import project_clock


class BrenaClockProjectionTests(unittest.TestCase):
    def test_matches_explicit_advance(self):
        original = BrenaWorld.new(seed=17)
        before = original.to_json()
        projected = project_clock(original, elapsed_minutes=1510)
        expected = BrenaWorld.new(seed=17)
        expected.advance_time(1510)
        self.assertEqual(projected.to_json(), expected.to_json())
        self.assertEqual(original.to_json(), before)

    def test_no_elapsed_time_is_frozen(self):
        original = BrenaWorld.new()
        self.assertEqual(project_clock(original, elapsed_minutes=0).to_json(), original.to_json())

    def test_rejects_invalid_elapsed(self):
        for value in (-1, 1.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    project_clock(BrenaWorld.new(), elapsed_minutes=value)

    def test_rejects_advanced_world_to_avoid_double_progression(self):
        world = BrenaWorld.new()
        world.advance_time(60)
        with self.assertRaises(ValueError):
            project_clock(world, elapsed_minutes=60)


if __name__ == "__main__":
    unittest.main()
