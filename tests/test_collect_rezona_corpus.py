import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import collect_rezona_corpus as collector  # noqa: E402


class CatalogTests(unittest.TestCase):
    def test_catalog_has_100_unique_mechanics_and_three_queries_each(self):
        catalog = json.loads((Path(__file__).resolve().parents[1] / "mechanics.json").read_text())
        mechanics = catalog["mechanics"]
        self.assertEqual(len(mechanics), 100)
        self.assertEqual(len({mechanic["id"] for mechanic in mechanics}), 100)
        self.assertTrue(all(len(mechanic["queries"]) >= 3 for mechanic in mechanics))

    def test_selection_preserves_record_and_api_order_while_deduplicating(self):
        mechanic = {"id": "example"}
        records = [
            {"payload": {"data": {"items": [
                {"game": {"game_id": 3, "game_version": 1}},
                {"game": {"game_id": 1, "game_version": 1}},
            ]}}},
            {"payload": {"data": {"items": [
                {"game": {"game_id": 1, "game_version": 1}},
                {"game": {"game_id": 2, "game_version": 1}},
            ]}}},
        ]
        selected, duplicates = collector.select_games(mechanic, records, maximum=3)
        self.assertEqual([game["game_id"] for game in selected], [3, 1, 2])
        self.assertEqual(duplicates, 1)


if __name__ == "__main__":
    unittest.main()
