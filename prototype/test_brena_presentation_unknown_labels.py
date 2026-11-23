"""Fail-closed presentation contract for unrecognized NPC codes.

A synthetic projection test; not Android HTTP or original EventStore execution.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from brena_presentation_payload import rana_status_payload


class UnknownLabelBoundaryTests(unittest.TestCase):
    def test_unknown_place_and_activity_are_not_echoed(self):
        view = SimpleNamespace(
            dialogue={"player_present": True},
            day=1, minute=120,
            npc_place="internal_secret_place",
            npc_activity="internal_secret_activity",
        )
        with patch("brena_presentation_payload.view_from_engine_state", return_value=view):
            result = rana_status_payload({})
        self.assertIsNone(result["place_label"])
        self.assertIsNone(result["activity_label"])
        self.assertNotIn("internal_secret_place", str(result))
        self.assertNotIn("internal_secret_activity", str(result))

    def test_known_codes_still_render(self):
        view = SimpleNamespace(
            dialogue={"player_present": True},
            day=1, minute=120,
            npc_place="square",
            npc_activity="spear_training",
        )
        with patch("brena_presentation_payload.view_from_engine_state", return_value=view):
            result = rana_status_payload({"player": {"location": "BRENA-SQUARE"}, "npcs": {"BRENA-RANA": {"location": "BRENA-SQUARE"}}})
        self.assertEqual(result["place_label"], "마을 광장")
        self.assertEqual(result["activity_label"], "창술 훈련")


if __name__ == "__main__":
    unittest.main()
