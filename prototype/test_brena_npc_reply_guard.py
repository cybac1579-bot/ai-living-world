import unittest
from brena_npc_reply_guard import validate_npc_reply


class ReplyGuardTests(unittest.TestCase):
    def setUp(self):
        self.prepared = {"expected_revision": 4, "npc_evidence": {"npc_id": "BRENA-RANA"}}

    def test_valid_npc_speech_is_normalized_without_writing(self):
        result = validate_npc_reply(self.prepared, {"npc_id": "BRENA-RANA", "speech": "  안녕.  "}, current_revision=4)
        self.assertEqual(result, {"speaker_id": "BRENA-RANA", "text": "안녕.", "source_revision": 4})

    def test_stale_revision_or_wrong_speaker_is_rejected(self):
        for revision in (3, 5, True):
            with self.assertRaises(ValueError):
                validate_npc_reply(self.prepared, {"npc_id": "BRENA-RANA", "speech": "안녕"}, current_revision=revision)
        with self.assertRaises(ValueError):
            validate_npc_reply(self.prepared, {"npc_id": "BRENA-SMITH", "speech": "안녕"}, current_revision=4)

    def test_player_action_and_unapproved_memory_fields_are_rejected(self):
        for field in ("player_action", "player_speech", "player_emotion", "memory", "relationship"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_npc_reply(self.prepared, {"npc_id": "BRENA-RANA", "speech": "안녕", field: "invented"}, current_revision=4)

    def test_empty_and_oversized_speech_is_rejected(self):
        for speech in ("", "  ", "x" * 2001, None):
            with self.assertRaises(ValueError):
                validate_npc_reply(self.prepared, {"npc_id": "BRENA-RANA", "speech": speech}, current_revision=4)


if __name__ == "__main__":
    unittest.main()
