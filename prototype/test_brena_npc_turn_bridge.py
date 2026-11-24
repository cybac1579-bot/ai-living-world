"""Test private dialogue turn preparation against authoritative state."""
import copy
import unittest
from brena_npc_turn_bridge import prepare_npc_turn


class Store:
    def __init__(self, state):
        self.state = state

    def load(self):
        return copy.deepcopy(self.state)


class NpcTurnBridgeTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "revision": 7, "world_minutes": 60,
            "player": {"location": "BRENA-CHIEF-HOUSE"},
            "npcs": {
                "BRENA-RANA": {"name": "라나", "location": "BRENA-CHIEF-HOUSE",
                               "brena_activity": "chief_house_life",
                               "memories": [{"text": "라나가 목격한 일", "revision": 2}]},
                "BRENA-SMITH": {"name": "대장장이", "location": "BRENA-SMITHY",
                                "memories": [{"text": "비공개 사건", "revision": 3}]},
            },
        }

    def test_player_text_and_npc_memory_are_kept_separate(self):
        before = copy.deepcopy(self.state)
        result = prepare_npc_turn(Store(self.state), "BRENA-RANA", "안녕, 라나.")
        self.assertEqual(result["expected_revision"], 7)
        self.assertEqual(result["player_text"], "안녕, 라나.")
        self.assertEqual(result["npc_evidence"]["activity_id"], "chief_house_life")
        self.assertNotIn("비공개 사건", str(result))
        self.assertEqual(self.state, before)

    def test_cannot_read_remote_npc_or_invent_player_text(self):
        with self.assertRaises(PermissionError):
            prepare_npc_turn(Store(self.state), "BRENA-SMITH", "안녕")
        for invalid in ("", " ", "a" * 2001, None):
            with self.assertRaises(ValueError):
                prepare_npc_turn(Store(self.state), "BRENA-RANA", invalid)

    def test_stale_turn_context_reloads_latest_revision(self):
        store = Store(self.state)
        first = prepare_npc_turn(store, "BRENA-RANA", "첫 대화")
        store.state["revision"] = 8
        second = prepare_npc_turn(store, "BRENA-RANA", "다음 대화")
        self.assertEqual((first["expected_revision"], second["expected_revision"]), (7, 8))


if __name__ == "__main__":
    unittest.main()
