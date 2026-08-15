import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import analyze_rezona_search_coverage as coverage  # noqa: E402


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def search_payload(ids, total):
    return {"code": 0, "data": {"total": total, "items": [{"game": {"game_id": game_id}} for game_id in ids]}}


class SearchCoverageTests(unittest.TestCase):
    def make_root(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        paths = {
            "alpha_one": "data/rezona/search/a/alpha/page-1.json",
            "alpha_two": "data/rezona/search/a/alpha/page-2.json",
            "alpha_repeat_one": "data/rezona/search/b/alpha/page-1.json",
            "alpha_repeat_two": "data/rezona/search/b/alpha/page-2.json",
            "beta_one": "data/rezona/search/b/beta/page-1.json",
            "beta_two": "data/rezona/search/b/beta/page-2.json",
        }
        write_json(root / paths["alpha_one"], search_payload([1, 2], 200))
        write_json(root / paths["alpha_two"], search_payload([3], 200))
        write_json(root / paths["alpha_repeat_one"], search_payload([2, 4], 200))
        write_json(root / paths["alpha_repeat_two"], search_payload([3], 200))
        write_json(root / paths["beta_one"], search_payload([4, 5], 2))
        write_json(root / paths["beta_two"], search_payload([], 2))
        index = {
            "collection_mode": "full",
            "retrieved_at": "2026-08-15T00:00:00Z",
            "unique_detail_games": 5,
            "mechanics": [
                {"searches": [{"query": "alpha", "path": paths["alpha_one"]}, {"query": "alpha", "path": paths["alpha_two"]}]},
                {"searches": [{"query": "alpha", "path": paths["alpha_repeat_one"]}, {"query": "alpha", "path": paths["alpha_repeat_two"]}, {"query": "beta", "path": paths["beta_one"]}, {"query": "beta", "path": paths["beta_two"]}]},
            ],
        }
        write_json(root / "data/rezona/index.json", index)
        return directory, root, paths

    def test_merges_repeated_terms_and_calculates_costs(self):
        directory, root, _ = self.make_root()
        with directory:
            result = coverage.analyze(root)
            metrics = result["search_coverage"]
            self.assertEqual(metrics["query_probes"], 3)
            self.assertEqual(metrics["distinct_query_terms"], 2)
            self.assertEqual(metrics["observed_unique_game_ids"], 5)
            self.assertEqual(metrics["term_memberships"], 6)
            self.assertEqual(metrics["single_term_games"], 4)
            self.assertEqual(metrics["two_term_games"], 1)
            self.assertEqual(metrics["capped_terms"], 1)
            self.assertEqual(metrics["pairwise_mean_intersection"], 1)
            sensitivity = result["overlap_sensitivity"]
            self.assertEqual(sensitivity["single_term_ids_f1"], 4)
            self.assertEqual(sensitivity["two_term_ids_f2"], 1)
            self.assertEqual(sensitivity["illustrative_value"], 13)
            self.assertIn("not an inventory estimate", sensitivity["status"])
            benchmarks = result["token_cost_benchmarks"]
            self.assertEqual(benchmarks["snapshot_date"], "2026-08-15")
            terra, sol = benchmarks["models"]
            self.assertEqual(terra["aggregate_multi_request_examples"][0]["cost_usd"], 1.0)
            self.assertEqual(terra["aggregate_multi_request_examples"][1]["cost_usd"], 10.0)
            self.assertEqual(sol["aggregate_multi_request_examples"][0]["cost_usd"], 1.00001)
            self.assertEqual(sol["aggregate_multi_request_examples"][1]["cost_usd"], 10.00001)
            raw = result["cost_scenarios"][2]
            self.assertEqual(raw["cost_usd_per_completed_indexed_game"], {"1": 5, "10": 50})

    def test_overlap_sensitivity_requires_doubletons(self):
        with self.assertRaisesRegex(coverage.SearchCoverageError, "requires at least one doubleton"):
            coverage.overlap_sensitivity(4, 4, 0)

    def test_output_is_deterministic(self):
        directory, root, _ = self.make_root()
        with directory:
            first = root / "first.json"
            second = root / "second.json"
            coverage.write_json(first, coverage.analyze(root))
            coverage.write_json(second, coverage.analyze(root))
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_fails_for_missing_search_source(self):
        directory, root, paths = self.make_root()
        with directory:
            (root / paths["beta_one"]).unlink()
            with self.assertRaisesRegex(coverage.SearchCoverageError, "Invalid JSON source"):
                coverage.analyze(root)


if __name__ == "__main__":
    unittest.main()
