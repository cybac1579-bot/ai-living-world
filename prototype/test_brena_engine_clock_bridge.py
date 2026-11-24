"""Original world clock is the only time authority for Brena read-only views."""
import unittest

from brena_engine_clock_bridge import view_from_engine_state


class BrenaEngineClockBridgeTests(unittest.TestCase):
    def test_engine_elapsed_minutes_determine_brena_time(self):
        initial = {"world_minutes": 0}
        later = {"world_minutes": 1500}
        before = initial.copy()
        view = view_from_engine_state(initial, "rana")
        self.assertEqual((view.day, view.minute), (1, 480))
        advanced = view_from_engine_state(later, "rana")
        self.assertEqual((advanced.day, advanced.minute), (2, 540))
        self.assertEqual(initial, before)

    def test_repeated_reads_do_not_advance_clock(self):
        state = {"world_minutes": 60}
        a = view_from_engine_state(state, "rana")
        b = view_from_engine_state(state, "rana")
        self.assertEqual(a, b)
        self.assertEqual(state["world_minutes"], 60)

    def test_legacy_missing_clock_is_frozen_at_initial_instant(self):
        state = {}
        view = view_from_engine_state(state, "rana")
        self.assertEqual((view.day, view.minute), (1, 480))
        self.assertEqual(state, {})

    def test_rejects_invalid_clock(self):
        for state in ({"world_minutes": -1}, {"world_minutes": True}, {"world_minutes": 1.5}):
            with self.subTest(state=state):
                with self.assertRaises((ValueError, KeyError)):
                    view_from_engine_state(state, "rana")


if __name__ == "__main__":
    unittest.main()
