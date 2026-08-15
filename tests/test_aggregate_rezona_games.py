import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import aggregate_rezona_games as aggregator  # noqa: E402


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def search_payload(game_id, version):
    return {"code": 0, "data": {"items": [{"type": "game", "game": {"game_id": game_id, "game_version": version}}]}}


class AggregateTests(unittest.TestCase):
    def make_root(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        detail = {"code": 0, "msg": "success", "data": {"game_id": 1, "game_version": 10, "name": "Game one"}}
        write_json(root / "data/rezona/game-details/1-10.json", detail)
        search_a = "data/rezona/search/parkour/parkour/page-1.json"
        search_b = "data/rezona/search/racing/racing/page-1.json"
        write_json(root / search_a, search_payload(1, 10))
        write_json(root / search_b, search_payload(1, 10))
        index = {
            "catalog_version": 1, "collection_mode": "full", "unique_detail_games": 1,
            "mechanics": [
                {"id": "parkour", "name": "Parkour", "selected_count": 1, "selected_game_ids": [1],
                 "detail_paths": {"1": "data/rezona/game-details/1-10.json"},
                 "searches": [{"query": "parkour", "page": 1, "path": search_a}]},
                {"id": "racing", "name": "Racing", "selected_count": 1, "selected_game_ids": [1],
                 "detail_paths": {"1": "data/rezona/game-details/1-10.json"},
                 "searches": [{"query": "racing", "page": 1, "path": search_b}]},
            ],
        }
        write_json(root / "data/rezona/index.json", index)
        return directory, root

    def test_merges_mechanics_and_keeps_observed_query_provenance(self):
        directory, root = self.make_root()
        with directory:
            output = aggregator.aggregate(root, root / "data/rezona/games.enriched.json", generated_at="2026-01-01T00:00:00Z")
            game = output["games"][0]
            self.assertEqual(output["summary"], {"unique_games": 1, "mechanic_memberships": 2, "keyword_space_memberships": 0, "provenance_entries": 2})
            self.assertEqual(game["game"], {"game_id": 1, "game_version": 10, "name": "Game one"})
            self.assertEqual(game["tags"]["mechanic_ids"], ["parkour", "racing"])
            self.assertEqual(game["tags"]["queries"], ["parkour", "racing"])
            self.assertEqual([entry["query"] for entry in game["provenance"]], ["parkour", "racing"])
            aggregator.validate(root, root / "data/rezona/games.enriched.json")

    def test_output_order_is_first_seen_source_order(self):
        directory, root = self.make_root()
        with directory:
            detail = {"code": 0, "data": {"game_id": 2, "game_version": 20, "name": "Game two"}}
            write_json(root / "data/rezona/game-details/2-20.json", detail)
            search_path = root / "data/rezona/search/parkour/parkour/page-1.json"
            write_json(search_path, {"data": {"items": [
                {"game": {"game_id": 2, "game_version": 20}}, {"game": {"game_id": 1, "game_version": 10}}
            ]}})
            index_path = root / "data/rezona/index.json"
            index = json.loads(index_path.read_text())
            index["unique_detail_games"] = 2
            index["mechanics"][0]["selected_count"] = 2
            index["mechanics"][0]["selected_game_ids"] = [2, 1]
            index["mechanics"][0]["detail_paths"]["2"] = "data/rezona/game-details/2-20.json"
            write_json(index_path, index)
            output = aggregator.aggregate(root, root / "data/rezona/games.enriched.json", generated_at="2026-01-01T00:00:00Z")
            self.assertEqual([record["game"]["game_id"] for record in output["games"]], [2, 1])

    def test_fails_when_selected_game_has_no_search_hit(self):
        directory, root = self.make_root()
        with directory:
            write_json(root / "data/rezona/search/parkour/parkour/page-1.json", {"data": {"items": []}})
            with self.assertRaisesRegex(aggregator.AggregationError, "no saved-search hit"):
                aggregator.aggregate(root, root / "data/rezona/games.enriched.json")


if __name__ == "__main__":
    unittest.main()
