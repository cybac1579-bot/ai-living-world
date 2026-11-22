import unittest

from brena_simulation import BrenaWorld
from brena_dialogue_context import dialogue_context


class DialogueContextTests(unittest.TestCase):
    def test_firsthand_memory_not_omniscience(self):
        world = BrenaWorld.new()
        world.record_event("player", "rana", "player helped rana")
        world.record_event("smith", "resident_a", "smith repaired a tool")
        rana = dialogue_context(world, "rana", player_place="chief_house")
        self.assertEqual([x["detail"] for x in rana["firsthand_events"]], ["player helped rana"])
        self.assertTrue(rana["player_present"])
        self.assertNotIn("smith repaired a tool", str(rana))

    def test_relationship_is_directional_and_private(self):
        world = BrenaWorld.new()
        world.set_relation("rana", "player", trust=3)
        world.set_relation("player", "rana", affection=9)
        context = dialogue_context(world, "rana")
        self.assertEqual(context["npc_view_of_player"], {"trust": 3})
        self.assertIsNone(context["player_view_of_npc"])
        self.assertIsNone(context["player_present"])

    def test_read_only_and_reload(self):
        world = BrenaWorld.new()
        world.record_event("player", "rana", "shared a meal")
        before = world.to_json()
        first = dialogue_context(world, "rana")
        self.assertEqual(world.to_json(), before)
        self.assertEqual(first, dialogue_context(BrenaWorld.from_json(before), "rana"))

    def test_invalid_npc_or_location(self):
        world = BrenaWorld.new()
        with self.assertRaises(KeyError):
            dialogue_context(world, "missing")
        with self.assertRaises(ValueError):
            dialogue_context(world, "rana", player_place="unknown")


if __name__ == "__main__":
    unittest.main()
