"""Regression for the real Android engine with a generated Brena initial state."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

try:
    from world_engine import EventStore, validate_state
except ModuleNotFoundError:
    EventStore = None


@unittest.skipIf(EventStore is None, "Android source not extracted")
class GeneratedBrenaStoreTests(unittest.TestCase):
    def test_invalid_player_destination_never_creates_store_revision(self):
        import world_engine
        from brena_player_navigation import validate_selected_destination
        repo = Path(__file__).resolve().parents[1]
        root = Path(world_engine.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "brena.json"
            subprocess.run(
                [sys.executable, str(repo / "tools" / "build_brena_initial_world.py"), str(root), str(output)],
                check=True, capture_output=True, text=True,
            )
            initial = json.loads(output.read_text(encoding="utf-8"))
            save_dir = Path(tmp) / "save"
            store = EventStore(save_dir)
            store.create(initial)
            with self.assertRaises(ValueError):
                validate_selected_destination(store.load(), "DEMO-FOREST")
            self.assertEqual(store.load(), initial)
            self.assertEqual(store.load()["revision"], 0)

    def test_player_travel_choices_from_real_generated_brena_world(self):
        import world_engine
        from brena_player_navigation import available_destinations, validate_selected_destination
        repo = Path(__file__).resolve().parents[1]
        root = Path(world_engine.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "brena.json"
            subprocess.run(
                [sys.executable, str(repo / "tools" / "build_brena_initial_world.py"), str(root), str(output)],
                check=True, capture_output=True, text=True,
            )
            state = json.loads(output.read_text(encoding="utf-8"))
            before = json.loads(json.dumps(state))
            offered = available_destinations(state)
            self.assertEqual(
                {item["id"] for item in offered},
                {"BRENA-GENERAL-STORE", "BRENA-INN", "BRENA-SMITHY",
                 "BRENA-CHIEF-HOUSE", "BRENA-GUARD-TRAINING-GROUND"},
            )
            self.assertEqual(validate_selected_destination(state, "BRENA-INN"), "BRENA-INN")
            for forbidden in ("DEMO-FOREST", "BRENA-SQUARE", "BRENA-UNKNOWN"):
                with self.assertRaises(ValueError):
                    validate_selected_destination(state, forbidden)
            self.assertEqual(state, before, "Listing and validating travel cannot move the player")

    def test_brena_routes_are_bidirectional_and_no_direction_is_invented(self):
        import world_engine
        repo = Path(__file__).resolve().parents[1]
        root = Path(world_engine.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "brena.json"
            subprocess.run(
                [sys.executable, str(repo / "tools" / "build_brena_initial_world.py"), str(root), str(output)],
                check=True, capture_output=True, text=True,
            )
            state = json.loads(output.read_text(encoding="utf-8"))
            regions = state["regions"]
            for region_id, region in regions.items():
                self.assertEqual(region["exits"], {}, "Do not invent unconfirmed compass directions")
                for destination in region["neighbors"]:
                    self.assertIn(destination, regions)
                    self.assertIn(region_id, regions[destination]["neighbors"])
            self.assertEqual(set(regions["BRENA-SQUARE"]["neighbors"]), set(regions) - {"BRENA-SQUARE"})
            self.assertEqual(state["player"]["location"], "BRENA-SQUARE")

    def test_rana_adjacent_move_commits_without_moving_player(self):
        import world_engine
        from brena_simulation import BrenaWorld
        from brena_event_adapter import movement_candidates
        repo = Path(__file__).resolve().parents[1]
        root = Path(world_engine.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "brena.json"
            subprocess.run(
                [sys.executable, str(repo / "tools" / "build_brena_initial_world.py"), str(root), str(output)],
                check=True, capture_output=True, text=True,
            )
            initial = json.loads(output.read_text(encoding="utf-8"))
            world = BrenaWorld.new()
            world.residents["rana"].place = "square"
            events = movement_candidates(
                world, initial,
                place_to_region={"square": "BRENA-SQUARE"},
                resident_to_npc={"rana": "BRENA-RANA"},
            )
            self.assertEqual(events, [{
                "type": "npc_move", "npc_id": "BRENA-RANA",
                "destination": "BRENA-SQUARE",
            }])
            save_dir = Path(tmp) / "save"
            store = EventStore(save_dir)
            store.create(initial)
            committed = store.commit(0, None, {"events": events}, mode="npc_tick")
            self.assertEqual(committed["player"], initial["player"])
            self.assertEqual(committed["npcs"]["BRENA-RANA"]["location"], "BRENA-SQUARE")
            cache = save_dir / "state.json"
            if cache.exists():
                cache.unlink()
            restored = EventStore(save_dir).load()
            self.assertEqual(restored, committed)
            self.assertEqual(restored["player"], initial["player"])

    def test_generated_world_survives_eventstore_restart(self):
        import world_engine
        repo = Path(__file__).resolve().parents[1]
        root = Path(world_engine.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "brena.json"
            subprocess.run(
                [sys.executable, str(repo / "tools" / "build_brena_initial_world.py"), str(root), str(output)],
                check=True, capture_output=True, text=True,
            )
            initial = json.loads(output.read_text(encoding="utf-8"))
            validate_state(initial)
            self.assertEqual(len(initial["regions"]), 6)
            self.assertEqual(len(initial["npcs"]), 7)
            self.assertEqual(initial["player"]["location"], "BRENA-SQUARE")
            self.assertEqual(initial["npcs"]["BRENA-RANA"]["location"], "BRENA-CHIEF-HOUSE")
            store_dir = Path(tmp) / "save"
            store = EventStore(store_dir)
            store.create(initial)
            first = store.load()
            self.assertEqual(first, initial)
            # Reading and reopening cannot advance the in-game clock or invent actions.
            cache = store_dir / "state.json"
            if cache.exists():
                cache.unlink()
            restored = EventStore(store_dir).load()
            self.assertEqual(restored, initial)
            self.assertEqual(restored["player"], initial["player"])
            self.assertEqual(restored["npcs"], initial["npcs"])


if __name__ == "__main__":
    unittest.main()
