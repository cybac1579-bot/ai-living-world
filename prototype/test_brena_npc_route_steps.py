"""NPC routing never teleports and respects disconnected maps."""
import unittest
from types import SimpleNamespace
from brena_event_adapter import movement_candidates


class RouteTests(unittest.TestCase):
    def test_two_hop_destination_moves_only_one_edge(self):
        world = SimpleNamespace(residents={"rana": SimpleNamespace(place="training")})
        state = {"regions": {
            "home": {"neighbors": ["square"]},
            "square": {"neighbors": ["home", "training"]},
            "training": {"neighbors": ["square"]}},
            "npcs": {"BRENA-RANA": {"location": "home"}}}
        result = movement_candidates(world, state,
            place_to_region={"home": "home", "square": "square", "training": "training"},
            resident_to_npc={"rana": "BRENA-RANA"})
        self.assertEqual(result, [{"type": "npc_move", "npc_id": "BRENA-RANA", "destination": "square"}])
        self.assertEqual(state["npcs"]["BRENA-RANA"]["location"], "home")

    def test_disconnected_destination_is_not_reached(self):
        world = SimpleNamespace(residents={"rana": SimpleNamespace(place="training")})
        state = {"regions": {"home": {"neighbors": []}, "training": {"neighbors": []}},
                 "npcs": {"BRENA-RANA": {"location": "home"}}}
        result = movement_candidates(world, state,
            place_to_region={"home": "home", "training": "training"},
            resident_to_npc={"rana": "BRENA-RANA"})
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
