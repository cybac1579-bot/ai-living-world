import unittest

from brena_event_adapter import movement_candidates
from brena_simulation import BrenaWorld


class MovementAdapterTests(unittest.TestCase):
    def setUp(self):
        self.world = BrenaWorld.new()
        self.engine = {
            "regions": {
                "village": {"neighbors": ["chief_house"]},
                "chief_house": {"neighbors": ["village"]},
                "forest": {"neighbors": []},
            },
            "npcs": {"rana": {"location": "village"}},
            "player": {"location": "village"},
        }
        self.mapping = {"chief_house": "chief_house", "square": "village", "inn": "forest"}

    def candidate(self):
        return movement_candidates(self.world, self.engine,
                                   place_to_region=self.mapping,
                                   resident_to_npc={"rana": "rana"})

    def test_adjacent_npc_movement_only(self):
        self.assertEqual(self.candidate(), [{"type": "npc_move", "npc_id": "rana", "destination": "chief_house"}])
        self.assertEqual(self.engine["npcs"]["rana"]["location"], "village")
        self.assertEqual(self.engine["player"]["location"], "village")

    def test_no_teleport_across_disconnected_regions(self):
        self.world.residents["rana"].place = "inn"
        self.assertEqual(self.candidate(), [])

    def test_unknown_mapping_is_not_a_move(self):
        self.world.residents["rana"].place = "guard_training_ground"
        self.assertEqual(self.candidate(), [])

    def test_already_present_does_not_move(self):
        self.world.residents["rana"].place = "square"
        self.assertEqual(self.candidate(), [])


if __name__ == "__main__":
    unittest.main()
