"""Integration smoke: Brena movement candidates through original EventStore.

Run from extracted Android source with PYTHONPATH pointing at prototype and src.
No player action is submitted, and no existing user store is opened.
"""
from __future__ import annotations

import tempfile
import json
import unittest
from pathlib import Path

from brena_event_adapter import movement_candidates
from brena_simulation import BrenaWorld
try:
    from world_engine import EventStore, validate_state
except ModuleNotFoundError:
    EventStore = None
    validate_state = None


@unittest.skipIf(EventStore is None, 'original Android engine not unpacked in prototype-only job')
class OriginalEngineIntegrationTests(unittest.TestCase):
    def test_duplicate_npc_mapping_is_rejected_before_event_creation(self):
        world = BrenaWorld.new()
        with self.assertRaisesRegex(ValueError, "distinct original NPCs"):
            movement_candidates(
                world, {"regions": {}, "npcs": {}},
                place_to_region={"square": "square_region"},
                resident_to_npc={"rana": "same", "chief": "same"},
            )

    def test_duplicate_place_mapping_is_rejected_before_event_creation(self):
        world = BrenaWorld.new()
        with self.assertRaisesRegex(ValueError, "distinct original regions"):
            movement_candidates(
                world, {"regions": {}, "npcs": {}},
                place_to_region={"square": "same", "inn": "same"},
                resident_to_npc={"rana": "rana"},
            )

    def test_movement_candidate_commits_and_replays(self):
        # The original Android source includes test fixtures; use its own
        # validated initial state, not an invented engine schema.
        import world_engine
        example_dir = Path(world_engine.__file__).resolve().parent / 'examples'
        states = []
        for fixture in sorted(example_dir.glob('*.json')):
            try:
                candidate = json.loads(fixture.read_text(encoding='utf-8'))
                validate_state(candidate)
                if candidate['revision'] == 0:
                    states.append(candidate)
            except (ValueError, KeyError, TypeError):
                continue
        self.assertTrue(states, 'No valid revision-zero original engine fixture found')
        state = states[0]
        validate_state(state)
        world = BrenaWorld.new(seed=3)
        # A known NPC and a registered adjacent region from the original
        # fixture are required; skip rather than inventing geography.
        npc_id = next(iter(state["npcs"]))
        origin = state["npcs"][npc_id]["location"]
        adjacent = state["regions"][origin].get("neighbors", [])
        self.assertTrue(adjacent, "Original fixture needs adjacent NPC region; integration must run")
        world.residents["rana"].place = "chief_house"
        candidates = movement_candidates(
            world, state,
            place_to_region={"chief_house": adjacent[0]},
            resident_to_npc={"rana": npc_id},
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["type"], "npc_move")
        player_before = state["player"]["location"]
        with tempfile.TemporaryDirectory() as directory:
            store = EventStore(Path(directory))
            store.create(state)
            committed = store.commit(0, None, {"events": candidates}, mode="npc_tick")
            journal = Path(directory) / "events.jsonl"
            self.assertTrue(journal.exists())
            self.assertIn("npc_move", journal.read_text(encoding="utf-8"))
            cache = Path(directory) / "state.json"
            if cache.exists():
                cache.unlink()  # prove journal replay, not a cached state read
            reloaded = EventStore(Path(directory)).load()
            self.assertEqual(committed, reloaded)
            self.assertEqual(reloaded["npcs"][npc_id]["location"], adjacent[0])
            self.assertEqual(reloaded["player"]["location"], player_before)
            self.assertEqual(reloaded.get("player_action_history"), state.get("player_action_history"))
            self.assertEqual(reloaded["revision"], 1)


if __name__ == "__main__":
    unittest.main()
