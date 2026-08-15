#!/usr/bin/env python3
"""Create the deduplicated enriched Rezona dataset from both saved collections."""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

INDEX_PATH = Path("data/rezona/index.json")
KEYWORD_INDEX_PATH = Path("data/rezona/keyword-space-index.json")
OUTPUT_PATH = Path("data/rezona/games.enriched.json")


class AggregationError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise AggregationError(f"Invalid JSON source: {path}") from error
    if not isinstance(value, dict):
        raise AggregationError(f"JSON source is not an object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def search_hit(root: Path, searches: list[dict[str, Any]], game_id: int, game_version: int | None) -> tuple[dict[str, Any], int]:
    for search in searches:
        for position, item in enumerate(read_json(root / search["path"]).get("data", {}).get("items", []), start=1):
            hit = item.get("game", {}) if isinstance(item, dict) else {}
            if hit.get("game_id") == game_id and (game_version is None or hit.get("game_version") == game_version):
                return search, position
    raise AggregationError(f"Selected game {game_id}/{game_version} has no saved-search hit")


def add_record(records: OrderedDict, game: dict[str, Any], provenance: dict[str, Any], first_seen: tuple[int, int]) -> None:
    identity = (game.get("game_id"), game.get("game_version"))
    if not isinstance(identity[0], int):
        raise AggregationError("Detail payload lacks game_id")
    if identity not in records:
        records[identity] = {"game": game, "tags": {"mechanic_ids": [], "mechanics": [], "queries": [], "collection_ids": [], "discovery_methods": []}, "provenance": [], "_first_seen": first_seen}
    record = records[identity]
    if record["game"] != game:
        raise AggregationError(f"Conflicting detail payload for {identity}")
    tags = record["tags"]
    for key, value in (("collection_ids", provenance["collection_id"]), ("discovery_methods", provenance["discovery_method"]), ("queries", provenance["query"])):
        if value not in tags[key]: tags[key].append(value)
    if "mechanic_id" in provenance and provenance["mechanic_id"] not in tags["mechanic_ids"]:
        tags["mechanic_ids"].append(provenance["mechanic_id"])
        tags["mechanics"].append({"id": provenance["mechanic_id"], "name": provenance["mechanic_name"]})
    record["provenance"].append(provenance)


def aggregate(root: Path, output_path: Path, generated_at: str | None = None) -> dict[str, Any]:
    index = read_json(root / INDEX_PATH)
    keyword = read_json(root / KEYWORD_INDEX_PATH) if (root / KEYWORD_INDEX_PATH).exists() else {"searches": [], "details": [], "selected_detail_ids": []}
    records: OrderedDict[tuple[int, int | None], dict[str, Any]] = OrderedDict()
    mechanic_memberships = keyword_memberships = 0
    for mechanic_position, mechanic in enumerate(index.get("mechanics", []), start=1):
        selected = mechanic.get("selected_game_ids", [])
        if mechanic.get("selected_count") != len(selected) or len(selected) != len(set(selected)):
            raise AggregationError(f"Invalid selected IDs for mechanic {mechanic.get('id')}")
        for rank, game_id in enumerate(selected, start=1):
            path = mechanic.get("detail_paths", {}).get(str(game_id))
            if not path: raise AggregationError(f"Selected game {game_id} has no detail path")
            game = read_json(root / path).get("data")
            if not isinstance(game, dict) or game.get("game_id") != game_id: raise AggregationError(f"Detail identity mismatch for {game_id}")
            search, pos = search_hit(root, mechanic["searches"], game_id, game.get("game_version"))
            add_record(records, game, {"collection_id": "mechanics-full", "discovery_method": "mechanics_catalog", "mechanic_id": mechanic["id"], "mechanic_name": mechanic["name"], "query": search["query"], "page": search["page"], "item_position": pos, "selected_rank": rank, "search_path": search["path"]}, (mechanic_position, rank))
            mechanic_memberships += 1
    detail_paths = {entry.get("game_id"): entry.get("path") for entry in keyword.get("details", []) if entry.get("ok") is True}
    selected_keyword = keyword.get("selected_detail_ids", [])
    if len(selected_keyword) != len(set(selected_keyword)): raise AggregationError("Duplicate keyword selected game ID")
    for rank, game_id in enumerate(selected_keyword, start=1):
        path = detail_paths.get(game_id)
        if not path: raise AggregationError(f"Keyword selected game {game_id} has no successful detail path")
        game = read_json(root / path).get("data")
        if not isinstance(game, dict) or game.get("game_id") != game_id: raise AggregationError(f"Keyword detail identity mismatch for {game_id}")
        search, pos = search_hit(root, keyword.get("searches", []), game_id, game.get("game_version"))
        add_record(records, game, {"collection_id": "keyword-space-pilot", "discovery_method": "adaptive_title_keyword_space", "query": search["query"], "query_stratum": search.get("stratum"), "page": search["page"], "item_position": pos, "selected_rank": rank, "search_path": search["path"]}, (len(index.get("mechanics", [])) + 1, rank))
        keyword_memberships += 1
    games = []
    for record in records.values():
        record.pop("_first_seen")
        games.append(record)
    output = {"schema_version": 2, "generated_at": generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"), "source": {"collections": [{"id": "mechanics-full", "index_path": str(INDEX_PATH), "catalog_version": index.get("catalog_version"), "collection_mode": index.get("collection_mode")}, {"id": "keyword-space-pilot", "index_path": str(KEYWORD_INDEX_PATH), "catalog_path": keyword.get("catalog_path"), "collection_mode": "adaptive_keyword_space_pilot"}]}, "summary": {"unique_games": len(games), "mechanic_memberships": mechanic_memberships, "keyword_space_memberships": keyword_memberships, "provenance_entries": mechanic_memberships + keyword_memberships}, "games": games}
    write_json(output_path, output)
    return output


def validate(root: Path, output_path: Path) -> None:
    output, index = read_json(output_path), read_json(root / INDEX_PATH)
    keyword = read_json(root / KEYWORD_INDEX_PATH) if (root / KEYWORD_INDEX_PATH).exists() else {"selected_detail_ids": []}
    games = output.get("games")
    expected_mechanics = sum(m["selected_count"] for m in index.get("mechanics", []))
    expected_keyword = len(keyword.get("selected_detail_ids", []))
    expected_schema = 2 if (root / KEYWORD_INDEX_PATH).exists() else 2
    if output.get("schema_version") != expected_schema or not isinstance(games, list) or output.get("summary") != {"unique_games": len(games), "mechanic_memberships": expected_mechanics, "keyword_space_memberships": expected_keyword, "provenance_entries": expected_mechanics + expected_keyword}:
        raise AggregationError("Dataset summary or schema differs from source indexes")
    identities, mechanics_seen, keyword_seen = set(), 0, 0
    for record in games:
        game, tags, provenance = record.get("game"), record.get("tags"), record.get("provenance")
        if not isinstance(game, dict) or not isinstance(tags, dict) or not provenance: raise AggregationError("Game record lacks detail, tags, or provenance")
        identity = (game.get("game_id"), game.get("game_version"))
        if identity in identities: raise AggregationError(f"Duplicate aggregate identity {identity}")
        identities.add(identity)
        if not tags.get("queries") or not tags.get("collection_ids") or not tags.get("discovery_methods"): raise AggregationError(f"Incomplete tags for {identity}")
        for entry in provenance:
            items = read_json(root / entry["search_path"]).get("data", {}).get("items", [])
            pos = entry["item_position"] - 1
            if pos < 0 or pos >= len(items) or items[pos].get("game", {}).get("game_id") != identity[0]: raise AggregationError(f"Search hit mismatch for {identity}")
            if entry["query"] not in tags["queries"] or entry["collection_id"] not in tags["collection_ids"]: raise AggregationError(f"Tags omit provenance for {identity}")
            if entry["collection_id"] == "mechanics-full":
                if entry.get("mechanic_id") not in tags["mechanic_ids"]: raise AggregationError(f"Mechanic tag omitted for {identity}")
                mechanics_seen += 1
            elif entry["collection_id"] == "keyword-space-pilot": keyword_seen += 1
            else: raise AggregationError(f"Unknown collection for {identity}")
    if mechanics_seen != expected_mechanics or keyword_seen != expected_keyword: raise AggregationError("Unexpected provenance counts")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--root", type=Path, default=Path.cwd()); parser.add_argument("--output", type=Path, default=OUTPUT_PATH); parser.add_argument("--validate", action="store_true"); args = parser.parse_args()
    root = args.root.resolve(); output = args.output if args.output.is_absolute() else root / args.output
    try:
        if args.validate: validate(root, output); print(f"Validated {output.relative_to(root)}")
        else:
            result = aggregate(root, output); print(f"Wrote {output.relative_to(root)}: {result['summary']['unique_games']} games, {result['summary']['provenance_entries']} provenance entries")
    except AggregationError as error: raise SystemExit(f"Aggregation failed: {error}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
