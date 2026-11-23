"""Cross-boundary save/restore projection regression.

Simulates serialization of an original engine snapshot, not Android EventStore I/O.
No player action, clock tick, or NPC movement may occur during reload/read.
"""
import copy
import json
import unittest

from brena_presentation_payload import rana_status_payload
from brena_engine_clock_bridge import view_from_engine_state
from brena_player_navigation import available_destinations


class BrenaReloadProjectionTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "revision": 4,
            "world_minutes": 180,
            "player": {"location": "square"},
            "regions": {
                "square": {"name": "광장", "neighbors": ["inn"]},
                "inn": {"name": "여관", "neighbors": ["square"]},
            },
            "npcs": {"rana": {"location": "square"}},
        }

    def test_reload_does_not_advance_time_or_move_player(self):
        saved = json.dumps(self.snapshot, ensure_ascii=False)
        restored = json.loads(saved)
        before = copy.deepcopy(restored)
        first = view_from_engine_state(restored, "rana")
        second = view_from_engine_state(restored, "rana")
        self.assertEqual(first, second)
        self.assertEqual(restored, before)
        self.assertEqual(restored["world_minutes"], 180)
        self.assertEqual(restored["player"]["location"], "square")
        self.assertEqual(restored["revision"], 4)

    def test_navigation_and_npc_status_reads_do_not_change_saved_state(self):
        restored = json.loads(json.dumps(self.snapshot))
        before = copy.deepcopy(restored)
        self.assertEqual(available_destinations(restored), [{"id": "inn", "name": "여관"}])
        status = rana_status_payload(restored)
        self.assertFalse(status["player_present"])
        self.assertIsNone(status["activity_id"])
        self.assertEqual(restored, before)

    def test_only_explicit_clock_change_affects_projection(self):
        before = view_from_engine_state(self.snapshot, "rana")
        advanced = copy.deepcopy(self.snapshot)
        advanced["world_minutes"] += 60
        after = view_from_engine_state(advanced, "rana")
        self.assertNotEqual((before.day, before.minute), (after.day, after.minute))
        self.assertEqual(self.snapshot["world_minutes"], 180)


if __name__ == "__main__":
    unittest.main()
