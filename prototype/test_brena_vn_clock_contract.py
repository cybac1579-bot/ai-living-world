"""Regression for frozen clock, explicit time advance, and Rana status rendering."""
import copy
import unittest

from brena_presentation_payload import rana_status_payload


class RanaWorldClockUiTests(unittest.TestCase):
    def test_repeated_reads_are_stable_and_read_only(self):
        engine = {"world_minutes": 0, "player": {"location": "fixed", "history": []}}
        original = copy.deepcopy(engine)
        first = rana_status_payload(engine)
        for _ in range(20):
            self.assertEqual(rana_status_payload(engine), first)
        self.assertEqual(engine, original)

    def test_explicit_time_advancement_and_frozen_resume(self):
        engine = {"world_minutes": 0, "player": {"location": "fixed", "history": []}}
        first = rana_status_payload(engine)
        self.assertEqual((first["day"], first["minute"]), (1, 480))
        # Only the original engine's explicit elapsed clock is authoritative.
        engine["world_minutes"] = 60
        next_hour = rana_status_payload(engine)
        self.assertEqual((next_hour["day"], next_hour["minute"]), (1, 540))
        self.assertEqual(next_hour, rana_status_payload(copy.deepcopy(engine)))
        engine["world_minutes"] = 1440
        next_day = rana_status_payload(engine)
        self.assertEqual((next_day["day"], next_day["minute"]), (2, 480))
        self.assertEqual(engine["player"], {"location": "fixed", "history": []})

    def test_status_does_not_claim_player_presence_without_location(self):
        engine = {"world_minutes": 90}
        status = rana_status_payload(engine)
        self.assertFalse(status["player_present"])
        self.assertNotIn("dialogue", status)
        self.assertNotIn("player_action", status)

    def test_invalid_engine_clock_rejected(self):
        for value in (-1, True, 0.25, "30"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    rana_status_payload({"world_minutes": value})


if __name__ == "__main__":
    unittest.main()
