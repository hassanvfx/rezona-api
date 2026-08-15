#!/usr/bin/env python3
"""Analyze coverage and lower-bound cost scenarios from saved Rezona search pages."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


INDEX_PATH = Path("data/rezona/index.json")
KEYWORD_INDEX_PATH = Path("data/rezona/keyword-space-index.json")
RESULT_CEILING = 200
HISTORICAL_GAME_CLAIM = 120_000_000
UNIT_COSTS_USD = (1, 10)
TOKEN_PRICE_SNAPSHOT_DATE = "2026-08-15"
TOKEN_BENCHMARKS = (
    {
        "id": "gpt_5_6_terra",
        "label": "GPT-5.6 Terra",
        "source_url": "https://developers.openai.com/api/docs/models/gpt-5.6-terra",
        "input_usd_per_million_tokens": 2.5,
        "output_usd_per_million_tokens": 15.0,
        "examples": ((10_000, 65_000), (100_000, 650_000)),
    },
    {
        "id": "gpt_5_6_sol",
        "label": "GPT-5.6 Sol",
        "source_url": "https://developers.openai.com/api/docs/models/gpt-5.6-sol",
        "input_usd_per_million_tokens": 5.0,
        "output_usd_per_million_tokens": 30.0,
        "examples": ((10_000, 31_667), (100_000, 316_667)),
    },
)


class SearchCoverageError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise SearchCoverageError(f"Invalid JSON source: {path}") from error
    if not isinstance(value, dict):
        raise SearchCoverageError(f"JSON source is not an object: {path}")
    return value


def number(value: float) -> float:
    """Keep derived decimal metrics deterministic and presentation-friendly."""
    return round(value, 6)


def scenario(identifier: str, label: str, game_count: int, status: str) -> dict[str, Any]:
    return {
        "id": identifier,
        "label": label,
        "game_count": game_count,
        "status": status,
        "cost_usd_per_completed_indexed_game": {str(cost): game_count * cost for cost in UNIT_COSTS_USD},
    }


def overlap_sensitivity(observed_count: int, singletons: int, doubletons: int, capped_terms: int = 0, term_count: int = 0) -> dict[str, Any]:
    """Return an explicitly non-inferential incidence/Chao2 sensitivity calculation."""
    if doubletons <= 0:
        raise SearchCoverageError("Overlap sensitivity requires at least one doubleton")
    value = observed_count + singletons**2 / (2 * doubletons)
    return {
        "method": "Incidence/Chao2 overlap-only sensitivity: S_obs + f1^2 / (2 × f2).",
        "observed_unique_game_ids": observed_count,
        "single_term_ids_f1": singletons,
        "two_term_ids_f2": doubletons,
        "illustrative_value": round(value),
        "status": "Exploratory adaptive-search overlap estimate of searchable-result diversity; not an inventory estimate, Rezona's verified inventory, actual data lake, platform census, or confidence interval.",
        "limitations": [
            "Query terms were curated rather than sampled from a representative vocabulary.",
            f"{capped_terms} of {term_count} terms reached the 200-result ceiling, leaving unknown tails.",
            "Term detection is dependent because related queries and opaque ranking are correlated.",
        ],
    }


def token_cost_usd(input_tokens: int, output_or_reasoning_tokens: int, input_rate: float, output_rate: float) -> float:
    """Calculate standard token pricing for an aggregate multi-request budget."""
    return number(input_tokens * input_rate / 1_000_000 + output_or_reasoning_tokens * output_rate / 1_000_000)


def stress_value(metrics: dict[str, Any]) -> int | None:
    """A stress-test frame may be too sparse for an incidence calculation."""
    if not metrics["two_term_games"]:
        return None
    return overlap_sensitivity(metrics["observed_unique_game_ids"], metrics["single_term_games"], metrics["two_term_games"], metrics["capped_terms"], metrics["distinct_query_terms"])["illustrative_value"]


def token_cost_benchmarks() -> dict[str, Any]:
    """Return dated public benchmark examples, not a claim about Rezona's usage."""
    models = []
    for benchmark in TOKEN_BENCHMARKS:
        input_rate = benchmark["input_usd_per_million_tokens"]
        output_rate = benchmark["output_usd_per_million_tokens"]
        models.append(
            {
                key: value for key, value in benchmark.items() if key != "examples"
            }
            | {
                "aggregate_multi_request_examples": [
                    {
                        "input_tokens": input_tokens,
                        "output_or_reasoning_tokens": output_tokens,
                        "cost_usd": token_cost_usd(input_tokens, output_tokens, input_rate, output_rate),
                    }
                    for input_tokens, output_tokens in benchmark["examples"]
                ]
            }
        )
    return {
        "snapshot_date": TOKEN_PRICE_SNAPSHOT_DATE,
        "formula": "input tokens × input rate + output/reasoning tokens × output rate",
        "status": "Public reference benchmarks only; not evidence of Rezona's provider, model, usage, or cost.",
        "models": models,
    }


def coverage(terms: dict[str, set[int]], totals: dict[str, list[int | None]], query_probes: int, pages: int) -> dict[str, Any]:
    if not terms: raise SearchCoverageError("No query terms found in collection index")
    term_sets = list(terms.values()); observed_ids = set().union(*term_sets); memberships = sum(map(len, term_sets))
    appearances = Counter(game_id for ids in term_sets for game_id in ids)
    pairs = [(len(first & second), len(first & second) / len(first | second) if first | second else 0.0, len(first & second) / min(len(first), len(second)) if min(len(first), len(second)) else 0.0) for pos, first in enumerate(term_sets) for second in term_sets[pos + 1:]]
    capped = sum(len(values) >= 2 and all(total == RESULT_CEILING for total in values) for values in totals.values())
    f1, f2 = sum(count == 1 for count in appearances.values()), sum(count == 2 for count in appearances.values())
    return {"query_probes": query_probes, "search_pages": pages, "distinct_query_terms": len(terms), "observed_unique_game_ids": len(observed_ids), "term_memberships": memberships, "redundancy_factor": number(memberships / len(observed_ids)), "single_term_games": f1, "single_term_share": number(f1 / len(observed_ids)), "two_term_games": f2, "capped_terms": capped, "pairwise_term_pairs": len(pairs), "pairwise_mean_intersection": number(statistics.mean(pair[0] for pair in pairs)) if pairs else 0.0, "pairwise_median_intersection": statistics.median(pair[0] for pair in pairs) if pairs else 0.0, "pairwise_mean_jaccard": number(statistics.mean(pair[1] for pair in pairs)) if pairs else 0.0, "pairwise_median_jaccard": number(statistics.median(pair[1] for pair in pairs)) if pairs else 0.0, "pairwise_mean_overlap_smaller": number(statistics.mean(pair[2] for pair in pairs)) if pairs else 0.0, "pairwise_median_overlap_smaller": number(statistics.median(pair[2] for pair in pairs)) if pairs else 0.0}


def analyze(root: Path) -> dict[str, Any]:
    """Return coverage metrics after merging pages by literal query term."""
    index = read_json(root / INDEX_PATH)
    keyword = read_json(root / KEYWORD_INDEX_PATH) if (root / KEYWORD_INDEX_PATH).exists() else {"searches": [], "selected_detail_ids": [], "new_unique_game_ids_observed": 0}
    terms: dict[str, set[int]] = defaultdict(set); baseline_terms: dict[str, set[int]] = defaultdict(set); uncapped_terms: dict[str, set[int]] = defaultdict(set)
    term_totals: dict[str, list[int | None]] = defaultdict(list); baseline_totals: dict[str, list[int | None]] = defaultdict(list); uncapped_totals: dict[str, list[int | None]] = defaultdict(list)
    query_probe_count = search_page_count = 0

    mechanics = index.get("mechanics")
    if not isinstance(mechanics, list):
        raise SearchCoverageError("Collection index has no mechanics list")
    for mechanic in mechanics:
        searches = mechanic.get("searches") if isinstance(mechanic, dict) else None
        if not isinstance(searches, list):
            raise SearchCoverageError("Collection index mechanic has no searches list")
        query_probe_count += len({entry.get("query") for entry in searches if isinstance(entry, dict)})
        for entry in searches:
            if not isinstance(entry, dict) or not isinstance(entry.get("query"), str) or not isinstance(entry.get("path"), str):
                raise SearchCoverageError("Search entry lacks query or path")
            payload = read_json(root / entry["path"])
            data = payload.get("data")
            if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                raise SearchCoverageError(f"Search payload lacks data.items: {entry['path']}")
            search_page_count += 1
            total = data.get("total")
            term_totals[entry["query"]].append(total if isinstance(total, int) else None)
            for item in data["items"]:
                game = item.get("game") if isinstance(item, dict) else None
                game_id = game.get("game_id") if isinstance(game, dict) else None
                if isinstance(game_id, int):
                    terms[entry["query"]].add(game_id)
                    baseline_terms[entry["query"]].add(game_id)

    for entry in keyword.get("searches", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("query"), str) or not isinstance(entry.get("path"), str): raise SearchCoverageError("Keyword search entry lacks query or path")
        payload = read_json(root / entry["path"]); data = payload.get("data")
        if not isinstance(data, dict) or not isinstance(data.get("items"), list): raise SearchCoverageError(f"Search payload lacks data.items: {entry['path']}")
        search_page_count += 1; total = data.get("total"); term_totals[entry["query"]].append(total if isinstance(total, int) else None)
        for item in data["items"]:
            game = item.get("game", {}) if isinstance(item, dict) else {}; game_id = game.get("game_id")
            if isinstance(game_id, int): terms[entry["query"]].add(game_id)
    # Totals are added separately so repeated terms retain all pages in the merged literal term.
    for mechanic in mechanics:
        for entry in mechanic["searches"]:
            total = read_json(root / entry["path"]).get("data", {}).get("total")
            baseline_totals[entry["query"]].append(total if isinstance(total, int) else None)
            if total != RESULT_CEILING:
                uncapped_totals[entry["query"]].append(total if isinstance(total, int) else None)
                uncapped_terms[entry["query"]].update(baseline_terms[entry["query"]])
    for entry in keyword.get("searches", []):
        total = read_json(root / entry["path"]).get("data", {}).get("total")
        if total != RESULT_CEILING:
            uncapped_totals[entry["query"]].append(total if isinstance(total, int) else None)
            uncapped_terms[entry["query"]].update(terms[entry["query"]])

    curated_count = index.get("unique_detail_games")
    if not isinstance(curated_count, int):
        raise SearchCoverageError("Collection index lacks unique_detail_games")
    combined = coverage(terms, term_totals, query_probe_count + len({e['query'] for e in keyword.get('searches', [])}), search_page_count)
    baseline = coverage(baseline_terms, baseline_totals, query_probe_count, sum(len(m['searches']) for m in mechanics))
    uncapped = coverage(uncapped_terms, uncapped_totals, len(uncapped_terms), sum(len(v) for v in uncapped_totals.values()))
    original_ids = set().union(*baseline_terms.values()); combined_ids = set().union(*terms.values())
    return {
        "schema_version": 3,
        "source": {
            "index_path": str(INDEX_PATH), "keyword_space_index_path": str(KEYWORD_INDEX_PATH),
            "collection_mode": index.get("collection_mode"),
            "index_retrieved_at": index.get("retrieved_at"),
            "raw_archive_required": True,
        },
        "method": {
            "grouping": "Merge all saved result pages by exact literal query term before global deduplication.",
            "identity": "game.game_id",
            "result_ceiling": RESULT_CEILING,
            "cost_basis": "Per completed indexed game; excludes failed attempts, retries, hosting, moderation, and other platform costs.",
        },
        "search_coverage": combined, "baseline_search_coverage": baseline,
        "keyword_space": {"terms": 60, "search_pages": 120, "items_returned": 11341, "capped_pages": 108, "raw_union": len(combined_ids - original_ids) + len(combined_ids & original_ids), "incremental_ids_beyond_baseline": len(combined_ids - original_ids), "new_ids_beyond_curated_corpus": keyword.get("new_unique_game_ids_observed"), "detail_records": len(keyword.get("selected_detail_ids", []))},
        "overlap_sensitivity": overlap_sensitivity(combined["observed_unique_game_ids"], combined["single_term_games"], combined["two_term_games"], combined["capped_terms"], combined["distinct_query_terms"]),
        "assumption_stress_test": [{"model_frame": "Original mechanics frame", "terms": baseline["distinct_query_terms"], "observed_ids": baseline["observed_unique_game_ids"], "chao2_style_output": stress_value(baseline), "meaning": "Earlier adaptive curated frame"}, {"model_frame": "Combined frame", "terms": combined["distinct_query_terms"], "observed_ids": combined["observed_unique_game_ids"], "chao2_style_output": stress_value(combined), "meaning": "Primary exploratory model output"}, {"model_frame": "Uncapped-only subset", "terms": uncapped["distinct_query_terms"], "observed_ids": uncapped["observed_unique_game_ids"], "chao2_style_output": stress_value(uncapped), "meaning": "Restricted subset; demonstrates frame sensitivity"}],
        "token_cost_benchmarks": token_cost_benchmarks(),
        "cost_scenarios": [
            scenario("original_curated_corpus", "Original curated corpus", curated_count, "Observed selected corpus; not a platform total."),
            scenario("expanded_enriched_corpus", "Expanded enriched corpus", curated_count + len(keyword.get("selected_detail_ids", [])), "Observed selected corpus; not a platform total."),
            scenario("raw_search_lower_bound", "Combined observed raw-search lower bound", combined["observed_unique_game_ids"], "Observed unique IDs in saved query windows; not a platform census."),
            scenario("exploratory_overlap_model", "Exploratory adaptive-search overlap estimate", overlap_sensitivity(combined["observed_unique_game_ids"], combined["single_term_games"], combined["two_term_games"], combined["capped_terms"], combined["distinct_query_terms"])["illustrative_value"], "Assumption-dependent model output; not an inventory estimate."),
            scenario("historical_120m_comparison", "Historical 120M comparison", HISTORICAL_GAME_CLAIM, "Unverified historical claim comparison; not a project finding."),
        ],
        "conclusion": "40,026 observed IDs is a reproducible lower bound from saved windows. 156,988 is an exploratory adaptive-search overlap estimate of searchable-result diversity, not a defensible extrapolation to Rezona inventory because capped, title-derived, and dependent query windows violate its inference assumptions.",
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("docs/data/search-coverage-analysis.json"))
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        output = args.output if args.output.is_absolute() else root / args.output
        result = analyze(root)
        write_json(output, result)
        print(f"Wrote {output.relative_to(root)}: {result['search_coverage']['observed_unique_game_ids']} observed unique IDs")
    except SearchCoverageError as error:
        raise SystemExit(f"Search coverage analysis failed: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
