"""Regression for the actual Android /api/state patcher's fail-closed contract.

Uses a minimal source fixture, not a claim of real Android execution.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.patch_brena_vn_state import patch


ORIGINAL = """from world_engine import render_contract, WorldError
class Handler:
    def state(self):
        rendered = render_contract(self.store.load())
        payload = {
            "world": rendered,
        }
        return payload
"""


class AndroidStatePatchContractTests(unittest.TestCase):
    def test_state_patch_does_not_trust_client_location(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "vn_server.py"
            target.write_text(ORIGINAL, encoding="utf-8")
            patch(target)
            updated = target.read_text(encoding="utf-8")
            self.assertIn("engine_state = self.store.load()", updated)
            self.assertIn("rana_status_payload(engine_state)", updated)
            self.assertIn("available_destinations(engine_state)", updated)
            self.assertIn("from brena_player_navigation import available_destinations", updated)
            self.assertNotIn("player_place=request", updated)
            self.assertNotIn("player_place=params", updated)
            self.assertEqual(updated.count('"brena": {"rana":'), 1)

    def test_navigation_state_is_read_only_and_uses_engine_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "vn_server.py"
            target.write_text(ORIGINAL, encoding="utf-8")
            patch(target)
            updated = target.read_text(encoding="utf-8")
            self.assertIn('"destinations": available_destinations(engine_state)', updated)
            self.assertEqual(updated.count("self.store.load()"), 1)
            self.assertNotIn("self.store.commit(", updated)
            self.assertNotIn("player_move", updated)
            self.assertNotIn("world_minutes +", updated)

    def test_unrecognized_source_fails_without_partial_write(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "vn_server.py"
            original = ORIGINAL.replace('"world": rendered,', '"world_state": rendered,')
            target.write_text(original, encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "response shape"):
                patch(target)
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_second_patch_refuses_duplicate_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "vn_server.py"
            target.write_text(ORIGINAL, encoding="utf-8")
            patch(target)
            once = target.read_text(encoding="utf-8")
            with self.assertRaises(AssertionError):
                patch(target)
            self.assertEqual(target.read_text(encoding="utf-8"), once)


if __name__ == "__main__":
    unittest.main()
