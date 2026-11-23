"""Guard explicit travel against invented time, NPC movement and AI output.

This is a patch-source contract test, not an Android runtime replay.
"""
import tempfile
import unittest
from pathlib import Path

from tools.patch_brena_world_travel import patch


ENGINE = '''def transition(state, submission, model_output, mode):
    _require(mode in ("player", "npc_tick", "world_tick"), "unknown mode")
    result = copy.deepcopy(state)
    if mode == "world_tick":
        _require(submission is None, "bad")
    if mode == "world_tick":
        from autonomy import advance_clock
        return advance_clock(result)
'''


class ExplicitTravelContractTests(unittest.TestCase):
    def test_travel_requires_explicit_destination_and_empty_ai_events(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "world_engine.py"
            path.write_text(ENGINE)
            patch(path)
            source = path.read_text()
            self.assertIn('set(submission) == {"destination"}', source)
            self.assertIn('model_output == {"events": []}', source)
            self.assertIn('validate_selected_destination(state, submission["destination"])', source)
            travel = source.split('if mode == "player_travel":')[-1].split('if mode == "world_tick":')[0]
            self.assertIn('result["player"]["location"] = destination', travel)
            self.assertNotIn("world_minutes", travel)
            self.assertNotIn("advance_clock", travel)
            self.assertNotIn("npc_tick", travel)

    def test_unexpected_engine_anchor_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "world_engine.py"
            source = ENGINE.replace('("player", "npc_tick", "world_tick")', '("player", "world_tick")')
            path.write_text(source)
            with self.assertRaises(AssertionError):
                patch(path)
            self.assertEqual(path.read_text(), source)


if __name__ == "__main__":
    unittest.main()
