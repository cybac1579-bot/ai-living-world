"""Rana presentation must not mutate state or invent character dialogue."""
import unittest

from brena_presentation_payload import rana_status_payload


class RanaStatusPayloadTests(unittest.TestCase):
    def test_read_only_status(self):
        state = {"world_minutes": 0, "player": {"location": "unchanged"}}
        original = {"world_minutes": 0, "player": {"location": "unchanged"}}
        payload = rana_status_payload(state)
        self.assertEqual(state, original)
        self.assertEqual(payload["name"], "라나")
        self.assertEqual((payload["day"], payload["minute"]), (1, 480))
        self.assertIn("place_label", payload)
        self.assertIn("activity_label", payload)
        self.assertNotIn("dialogue", payload)
        self.assertNotIn("player_action", payload)

    def test_frozen_state_is_stable(self):
        state = {"world_minutes": 60}
        self.assertEqual(rana_status_payload(state), rana_status_payload(state))


if __name__ == "__main__":
    unittest.main()
