"""First-playable direction guard: protect living-world gameplay priorities.

These are source-level safeguards, NOT proof of Android gameplay or GPT integration.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FirstPlayableDirectionTests(unittest.TestCase):
    def test_world_tick_requires_explicit_player_request(self):
        ui = (ROOT / "tools/patch_brena_vn_ui.py").read_text(encoding="utf-8")
        api = (ROOT / "tools/patch_brena_vn_time.py").read_text(encoding="utf-8")
        self.assertIn("advanceBtn.addEventListener('click'", ui)
        self.assertIn("window.confirm('게임 시간을 '+minutes+'분 진행할까?')", ui)
        self.assertIn('mode="brena_world_tick"', api)
        self.assertIn('minutes not in (10, 60 - state.get("world_minutes", 0) % 60)', api)
        self.assertNotIn("Date.now(", ui)
        self.assertNotIn("setInterval(", ui)

    def test_npc_visibility_uses_authoritative_save(self):
        status = (ROOT / "prototype/brena_presentation_payload.py").read_text(encoding="utf-8")
        self.assertIn('engine_state.get("npcs", {}).get("BRENA-RANA"', status)
        self.assertIn('actual_player == actual_rana', status)

    def test_first_playable_requires_npc_memory_and_dialogue_not_just_ui(self):
        canonical = (ROOT / "docs/development/PROJECT_SOURCE_OF_TRUTH.md").read_text(encoding="utf-8")
        for required in ("독립", "기억", "대화", "저장", "Android"):
            self.assertIn(required, canonical)
        # This test does not pretend these systems are integrated.
        # Their end-to-end acceptance remains a release gate.


if __name__ == "__main__":
    unittest.main()
