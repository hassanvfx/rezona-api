#!/usr/bin/env python3
"""Collect a deterministic long-tail keyword-space discovery pilot."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import random
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import collect_rezona_corpus as corpus


CATALOG_PATH = Path("docs/data/keyword-space-pilot.json")
RAW_ROOT = Path("data/rezona/keyword-space")
STOP = {"the", "and", "for", "with", "game", "play", "your", "you", "from", "this", "that", "new", "fun", "into", "out", "all", "not", "are", "get", "one", "how", "but", "simulator"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_bytes())


def write_json(path: Path, value: dict[str, Any]) -> None:
    corpus.atomic_write(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())


def slug(value: str) -> str:
    base = "-".join("".join(char.lower() if char.isalnum() else " " for char in value).split())
    return f"{base}-{hashlib.sha256(value.encode()).hexdigest()[:8]}"


def existing_queries(root: Path) -> set[str]:
    mechanics = read_json(root / "mechanics.json")["mechanics"]
    return {query.lower() for mechanic in mechanics for query in mechanic["queries"]}


def candidate_terms(root: Path) -> dict[str, list[str]]:
    dataset = read_json(root / "data/rezona/games.enriched.json")
    known = existing_queries(root)
    words: Counter[str] = Counter()
    phrases: Counter[str] = Counter()
    for record in dataset["games"]:
        # Restrict expansion to the title lead, avoiding template/instruction text that
        # some generated game names append after the core searchable phrase.
        tokens = [token for token in re.findall(r"[a-z][a-z0-9]{2,}", str(record["game"].get("name", "")).lower()) if token not in STOP][:5]
        words.update(tokens)
        phrases.update(f"{first} {second}" for first, second in zip(tokens, tokens[1:]))
    return {
        "unigram": sorted(term for term, count in words.items() if 2 <= count <= 20 and term not in known),
        "bigram": sorted(term for term, count in phrases.items() if 2 <= count <= 20 and term not in known),
    }


def build_catalog(root: Path, count: int, seed: str) -> dict[str, Any]:
    candidates = candidate_terms(root)
    if count % 2 or len(candidates["unigram"]) < count // 2 or len(candidates["bigram"]) < count // 2:
        raise ValueError("Requested keyword-space sample cannot be drawn evenly from candidate strata")
    rng = random.Random(seed)
    terms = []
    for kind in ("unigram", "bigram"):
        terms.extend({"query": query, "stratum": kind} for query in rng.sample(candidates[kind], count // 2))
    return {"schema_version": 1, "study_id": "rezona-keyword-space-pilot-v1", "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "method": "Deterministic adaptive discovery sample drawn from long-tail unigram and bigram vocabulary in the existing enriched game-title corpus. It is not a probability sample of all Rezona games.",
            "seed": seed, "query_count": count, "candidate_counts": {kind: len(values) for kind, values in candidates.items()},
            "queries": sorted(terms, key=lambda item: (item["stratum"], item["query"]))}


def fetch_search(root: Path, catalog: dict[str, Any], entry: dict[str, str], page: int, token: str | None) -> dict[str, Any]:
    path = root / RAW_ROOT / catalog["study_id"] / "search" / slug(entry["query"]) / f"page-{page}.json"
    payload_bytes = path.read_bytes() if path.exists() else corpus.get_json("/search", {"type": "game", "q": entry["query"], "page": page, "size": 100}, token).payload
    if not path.exists():
        corpus.atomic_write(path, payload_bytes)
    payload = json.loads(payload_bytes)
    return {"query": entry["query"], "stratum": entry["stratum"], "page": page, "path": str(path.relative_to(root)), "payload": payload}


def fetch_detail(root: Path, catalog: dict[str, Any], game_id: int, token: str | None) -> dict[str, Any]:
    path = root / RAW_ROOT / catalog["study_id"] / "game-details" / f"{game_id}.json"
    try:
        payload_bytes = path.read_bytes() if path.exists() else corpus.get_json("/game/detail", {"game_id": game_id}, token).payload
        if not path.exists():
            corpus.atomic_write(path, payload_bytes)
        payload = json.loads(payload_bytes)
        return {"game_id": game_id, "path": str(path.relative_to(root)), "ok": payload.get("code") == 0}
    except (corpus.RequestFailure, OSError, json.JSONDecodeError) as error:
        return {"game_id": game_id, "path": None, "ok": False, "error": type(error).__name__}


def collect(root: Path, catalog: dict[str, Any], detail_limit: int, token_file: Path) -> int:
    token = corpus.load_access_token(root / token_file)
    jobs = [(entry, page) for entry in catalog["queries"] for page in (1, 2)]
    records: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_search, root, catalog, entry, page, token) for entry, page in jobs]
        records = [future.result() for future in concurrent.futures.as_completed(futures)]
    ordered = sorted(records, key=lambda item: (next(index for index, query in enumerate(catalog["queries"]) if query["query"] == item["query"]), item["page"]))
    existing = {record["game"].get("game_id") for record in read_json(root / "data/rezona/games.enriched.json")["games"]}
    new_ids: list[int] = []
    seen = set(existing)
    for record in ordered:
        for item in record["payload"].get("data", {}).get("items", []):
            game = item.get("game") if isinstance(item, dict) else None
            game_id = game.get("game_id") if isinstance(game, dict) else None
            if isinstance(game_id, int) and game_id not in seen:
                seen.add(game_id)
                new_ids.append(game_id)
    selected = new_ids[:detail_limit]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        details = [future.result() for future in concurrent.futures.as_completed([executor.submit(fetch_detail, root, catalog, game_id, token) for game_id in selected])]
    index = {"schema_version": 1, "study_id": catalog["study_id"], "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "catalog_path": str(CATALOG_PATH), "searches": [{key: value for key, value in record.items() if key != "payload"} for record in ordered],
             "new_unique_game_ids_observed": len(new_ids), "detail_limit": detail_limit, "selected_detail_ids": selected,
             "details": sorted(details, key=lambda item: item["game_id"])}
    write_json(root / "data/rezona/keyword-space-index.json", index)
    print(f"Keyword-space search complete: {len(new_ids)} new IDs observed; {sum(item['ok'] for item in details)} detail responses archived; token={'configured' if token else 'not configured'}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    parser.add_argument("--token-file", type=Path, default=Path(".rezona.local.env"))
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--seed", default="rezona-keyword-space-pilot-v1")
    parser.add_argument("--detail-limit", type=int, default=2000)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--collect", action="store_true")
    args = parser.parse_args()
    if args.build == args.collect:
        parser.error("choose exactly one of --build or --collect")
    root = args.root.resolve()
    catalog_path = args.catalog if args.catalog.is_absolute() else root / args.catalog
    if args.build:
        write_json(catalog_path, build_catalog(root, args.count, args.seed))
        print(f"Wrote {catalog_path.relative_to(root)}")
        return 0
    return collect(root, read_json(catalog_path), args.detail_limit, args.token_file)


if __name__ == "__main__":
    raise SystemExit(main())
