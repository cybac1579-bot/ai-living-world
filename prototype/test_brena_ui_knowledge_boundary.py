"""Guard against accidentally showing remote NPC locations in the VN header.

This is a source contract test; Android screenshot/behavior still needs testing.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RanaKnowledgeBoundaryTests(unittest.TestCase):
    def test_ui_requires_explicit_player_presence(self):
        source = (ROOT / "tools/patch_brena_vn_ui.py").read_text(encoding="utf-8")
        self.assertIn("rana.player_present === true", source)
        self.assertIn("ranaBadge.hidden", source)
        self.assertNotIn("'라나 · '+rana.place_label", source)

    def test_payload_does_not_assume_player_is_present(self):
        from brena_presentation_payload import rana_status_payload
        result = rana_status_payload({"world_minutes": 0})
        self.assertIs(result["player_present"], False)
        self.assertNotIn("dialogue", result)
        for key in ("place_id", "place_label", "activity_id", "activity_label"):
            self.assertIsNone(result[key], key)

    def test_remote_npc_location_is_redacted_even_with_player_elsewhere(self):
        from brena_presentation_payload import rana_status_payload
        result = rana_status_payload({"world_minutes": 0}, player_place="non_matching_place")
        self.assertIs(result["player_present"], False)
        for key in ("place_id", "place_label", "activity_id", "activity_label"):
            self.assertIsNone(result[key], key)


if __name__ == "__main__":
    unittest.main()
