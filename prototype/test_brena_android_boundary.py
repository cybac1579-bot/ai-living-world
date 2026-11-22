"""No implicit player actions or writes at the Brena/Android boundary."""
import unittest

from brena_android_boundary import advance_explicit, npc_view
from brena_simulation import BrenaWorld


class AndroidBoundaryTests(unittest.TestCase):
    def test_view_is_read_only(self):
        world = BrenaWorld.new()
        before = world.to_json()
        view = npc_view(world, "rana", player_place="square")
        self.assertEqual((view.day, view.minute), (1, 480))
        self.assertEqual(view.npc_id, "rana")
        self.assertEqual(world.to_json(), before)
        self.assertEqual(world.events, [])

    def test_explicit_time_creates_new_state_without_mutating_original(self):
        world = BrenaWorld.new(seed=7)
        before = world.to_json()
        advanced = advance_explicit(world, 60)
        self.assertEqual(world.to_json(), before)
        self.assertEqual(advanced.minute, 540)
        self.assertEqual(advanced.events, [])
        self.assertEqual(advanced.to_json(), advance_explicit(world, 60).to_json())

    def test_invalid_time_does_not_change_state(self):
        world = BrenaWorld.new()
        before = world.to_json()
        with self.assertRaises(ValueError):
            advance_explicit(world, -1)
        self.assertEqual(world.to_json(), before)


if __name__ == "__main__":
    unittest.main()
