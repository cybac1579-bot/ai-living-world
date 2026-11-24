"""Player travel must be an explicit choice, never autonomous movement."""
import copy
import unittest

from brena_player_navigation import available_destinations, validate_selected_destination


class BrenaPlayerNavigationTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "player": {"location": "BRENA-SQUARE", "health": 10},
            "regions": {
                "BRENA-SQUARE": {"name": "브레나 광장", "neighbors": ["BRENA-INN", "BRENA-SMITHY"]},
                "BRENA-INN": {"name": "브레나 여관", "neighbors": ["BRENA-SQUARE"]},
                "BRENA-SMITHY": {"name": "브레나 대장간", "neighbors": ["BRENA-SQUARE"]},
                "DEMO-CAMP": {"name": "테스트 야영지", "neighbors": []},
            },
        }

    def test_only_neighboring_destinations_are_offered(self):
        before = copy.deepcopy(self.state)
        self.assertEqual(
            available_destinations(self.state),
            [{"id": "BRENA-INN", "name": "브레나 여관"},
             {"id": "BRENA-SMITHY", "name": "브레나 대장간"}],
        )
        self.assertEqual(self.state, before)

    def test_selected_destination_is_validated_without_player_mutation(self):
        before = copy.deepcopy(self.state)
        self.assertEqual(validate_selected_destination(self.state, "BRENA-INN"), "BRENA-INN")
        self.assertEqual(self.state, before)

    def test_unconnected_region_cannot_be_selected(self):
        for destination in ("DEMO-CAMP", "BRENA-SQUARE", "BRENA-UNKNOWN", None):
            with self.subTest(destination=destination):
                with self.assertRaises(ValueError):
                    validate_selected_destination(self.state, destination)
        self.assertEqual(self.state["player"]["location"], "BRENA-SQUARE")

    def test_duplicate_and_self_links_are_not_offered(self):
        self.state["regions"]["BRENA-SQUARE"]["neighbors"] = [
            "BRENA-INN", "BRENA-INN", "BRENA-SQUARE", "BRENA-SMITHY"
        ]
        self.assertEqual(available_destinations(self.state), [
            {"id": "BRENA-INN", "name": "브레나 여관"},
            {"id": "BRENA-SMITHY", "name": "브레나 대장간"},
        ])

    def test_invalid_neighbor_is_rejected_before_offering_travel(self):
        for bad in ("BRENA-UNKNOWN", None, 123):
            with self.subTest(bad=bad):
                self.state["regions"]["BRENA-SQUARE"]["neighbors"] = [bad]
                with self.assertRaises(ValueError):
                    available_destinations(self.state)

    def test_return_route_is_available_after_engine_changes_location(self):
        self.state["player"]["location"] = "BRENA-INN"
        self.assertEqual(available_destinations(self.state), [
            {"id": "BRENA-SQUARE", "name": "브레나 광장"}
        ])


if __name__ == "__main__":
    unittest.main()
