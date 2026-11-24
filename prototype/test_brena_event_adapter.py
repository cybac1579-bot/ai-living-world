import unittest
import copy

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

    def test_candidate_generation_does_not_mutate_world_or_engine(self):
        before_engine = copy.deepcopy(self.engine)
        before_world = self.world.to_json()
        first = self.candidate()
        second = self.candidate()
        self.assertEqual(first, second)
        self.assertEqual(self.engine, before_engine)
        self.assertEqual(self.world.to_json(), before_world)

    def test_duplicate_npc_mapping_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct original NPCs"):
            movement_candidates(
                self.world, self.engine,
                place_to_region=self.mapping,
                resident_to_npc={"rana": "rana", "another": "rana"},
            )

    def test_unknown_npc_is_skipped_without_inventing_character(self):
        self.assertEqual(
            movement_candidates(
                self.world, self.engine,
                place_to_region=self.mapping,
                resident_to_npc={"rana": "unknown_npc"},
            ), [],
        )
        self.assertEqual(set(self.engine["npcs"]), {"rana"})

    def test_missing_graph_link_never_teleports_npc(self):
        self.engine["regions"]["village"]["neighbors"] = []
        self.assertEqual(self.candidate(), [])
        self.assertEqual(self.engine["npcs"]["rana"]["location"], "village")

    def test_already_present_does_not_move(self):
        self.world.residents["rana"].place = "square"
        self.assertEqual(self.candidate(), [])


if __name__ == "__main__":
    unittest.main()
