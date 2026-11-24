"""Knowledge-boundary regression for Android NPC dialogue evidence."""
import copy
import unittest

from brena_engine_dialogue_evidence import npc_dialogue_evidence


class EngineDialogueEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "world_minutes": 60,
            "player": {"location": "BRENA-CHIEF-HOUSE"},
            "npcs": {
                "BRENA-RANA": {"name": "라나", "location": "BRENA-CHIEF-HOUSE",
                               "brena_activity": "personal_rest",
                               "memories": [{"text": "플레이어와 대화함", "revision": 3}]},
                "BRENA-SMITH": {"name": "대장장이", "location": "BRENA-SMITHY",
                                "memories": [{"text": "비밀 소문", "revision": 2}]},
            },
        }

    def test_only_firsthand_memories_and_saved_activity(self):
        before = copy.deepcopy(self.state)
        result = npc_dialogue_evidence(self.state, "BRENA-RANA")
        self.assertEqual(result["activity_id"], "personal_rest")
        self.assertEqual(result["firsthand_memories"], [{"text": "플레이어와 대화함", "revision": 3}])
        self.assertNotIn("비밀 소문", str(result))
        self.assertEqual(self.state, before)

    def test_remote_npc_cannot_be_queried(self):
        with self.assertRaises(PermissionError):
            npc_dialogue_evidence(self.state, "BRENA-SMITH")
        with self.assertRaises(KeyError):
            npc_dialogue_evidence(self.state, "UNKNOWN")

    def test_no_inferred_player_state_or_invented_activity(self):
        del self.state["npcs"]["BRENA-RANA"]["brena_activity"]
        result = npc_dialogue_evidence(self.state, "BRENA-RANA")
        self.assertIsNone(result["activity_id"])
        self.assertNotIn("player_emotion", result)
        self.assertNotIn("player_action", result)


if __name__ == "__main__":
    unittest.main()
