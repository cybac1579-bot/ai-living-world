"""Integration smoke: Brena movement candidates through original EventStore.

Run from extracted Android source with PYTHONPATH pointing at prototype and src.
No player action is submitted, and no existing user store is opened.
"""
from __future__ import annotations

import tempfile
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
    def test_movement_candidate_commits_and_replays(self):
        # The original Android source includes test fixtures; use its own
        # validated initial state, not an invented engine schema.
        from tests.test_engine import sample_state
        state = sample_state()
        validate_state(state)
        world = BrenaWorld.new(seed=3)
        # A known NPC and a registered adjacent region from the original
        # fixture are required; skip rather than inventing geography.
        npc_id = next(iter(state["npcs"]))
        origin = state["npcs"][npc_id]["location"]
        adjacent = state["regions"][origin].get("neighbors", [])
        if not adjacent:
            self.skipTest("Original fixture has no adjacent NPC region")
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
            committed = store.commit(0, None, {"events": candidates}, mode="world_tick")
            reloaded = EventStore(Path(directory)).load()
            self.assertEqual(committed, reloaded)
            self.assertEqual(reloaded["npcs"][npc_id]["location"], adjacent[0])
            self.assertEqual(reloaded["player"]["location"], player_before)
            self.assertEqual(reloaded["revision"], 1)


if __name__ == "__main__":
    unittest.main()
