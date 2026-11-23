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

    def test_vn_clock_uses_only_authoritative_game_time(self):
        source = (ROOT / "tools/patch_brena_vn_ui.py").read_text(encoding="utf-8")
        self.assertIn("brena-world-clock", source)
        self.assertIn("clock.day", source)
        self.assertIn("clock.minute", source)
        self.assertNotIn("Date.now(", source)
        self.assertNotIn("new Date(", source)

    def test_payload_does_not_assume_player_is_present(self):
        from brena_presentation_payload import rana_status_payload
        result = rana_status_payload({"world_minutes": 0})
        self.assertIs(result["player_present"], False)
        self.assertNotIn("dialogue", result)
        for key in ("place_id", "place_label", "activity_id", "activity_label"):
            self.assertIsNone(result[key], key)

    def test_rana_is_visible_only_at_same_place_without_changing_save(self):
        from brena_presentation_payload import rana_status_payload
        original = {"world_minutes": 0, "player": {"region": "unchanged"}}
        snapshot = repr(original)
        visible = rana_status_payload(original, player_place="chief_house")
        self.assertIs(visible["player_present"], True)
        self.assertEqual(visible["place_id"], "chief_house")
        self.assertEqual(visible["name"], "라나")
        self.assertEqual(repr(original), snapshot)
        hidden = rana_status_payload(original, player_place="square")
        self.assertIs(hidden["player_present"], False)
        self.assertIsNone(hidden["place_id"])
        self.assertEqual(repr(original), snapshot)

    def test_every_simulation_activity_has_a_korean_presentation_label(self):
        from brena_simulation import ACTIVITIES
        from brena_presentation_payload import KNOWN_ACTIVITIES
        self.assertTrue(set(ACTIVITIES).issubset(KNOWN_ACTIVITIES))
        for activity in ACTIVITIES:
            self.assertNotEqual(KNOWN_ACTIVITIES[activity], activity)

    def test_all_rana_simulation_activities_have_localized_labels(self):
        from brena_simulation import ACTIVITIES
        from brena_presentation_payload import KNOWN_ACTIVITIES
        self.assertEqual(set(ACTIVITIES) | {"idle"}, set(KNOWN_ACTIVITIES))
        self.assertTrue(all(KNOWN_ACTIVITIES[a] for a in ACTIVITIES))

    def test_remote_npc_location_is_redacted_even_with_player_elsewhere(self):
        from brena_presentation_payload import rana_status_payload
        result = rana_status_payload({"world_minutes": 0}, player_place="square")
        self.assertIs(result["player_present"], False)
        for key in ("place_id", "place_label", "activity_id", "activity_label"):
            self.assertIsNone(result[key], key)


if __name__ == "__main__":
    unittest.main()
