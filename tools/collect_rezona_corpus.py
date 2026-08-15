#!/usr/bin/env python3
"""Collect a reproducible Rezona game-mechanics corpus.

Raw response bytes are retained as received.  The derived index is the only
normalised artifact; it records deterministic catalogue/API ordering.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_ROOT = "https://api.rezona.ai/api/v3"
PILOT_IDS = (
    "parkour", "endless-runner", "clicker", "idle", "merge", "match-3",
    "tower-defense", "crafting-survival", "racing", "dress-up", "rhythm",
    "social-deduction",
)


@dataclass(frozen=True)
class Response:
    payload: bytes
    authenticated: bool


class RequestFailure(RuntimeError):
    pass


def load_access_token(token_file: Path) -> str | None:
    """Read only REZONA_ACCESS_TOKEN; never print the file or its value."""
    value = os.environ.get("REZONA_ACCESS_TOKEN", "").strip()
    if value:
        return value
    if not token_file.exists():
        return None
    for line in token_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("REZONA_ACCESS_TOKEN="):
            value = line.partition("=")[2].strip()
            if value and value != "<redacted>":
                return value
    return None


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def get_json(endpoint: str, params: dict[str, Any], token: str | None) -> Response:
    """Fetch JSON with bounded retries; retry anonymous after an auth failure."""
    attempts: list[tuple[bool, str | None]] = [(bool(token), token)]
    if token:
        attempts.append((False, None))
    last_error = "unknown request failure"
    for authenticated, active_token in attempts:
        headers = {"Accept": "application/json", "x-os": "ios"}
        if active_token:
            headers["Authorization"] = f"Bearer {active_token}"
        url = f"{API_ROOT}{endpoint}?{urlencode(params)}"
        for retry in range(4):
            try:
                request = Request(url, headers=headers)
                with urlopen(request, timeout=30) as result:
                    payload = result.read()
                json.loads(payload)
                return Response(payload=payload, authenticated=authenticated)
            except HTTPError as error:
                last_error = f"HTTP {error.code} for {endpoint}"
                if error.code in (401, 403) and authenticated:
                    break
                if error.code not in (408, 429, 500, 502, 503, 504):
                    break
            except (URLError, TimeoutError, json.JSONDecodeError) as error:
                last_error = f"{type(error).__name__} for {endpoint}"
            time.sleep(1.0 * (2 ** retry))
    raise RequestFailure(last_error)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_bytes())


def query_slug(query: str) -> str:
    return "-".join("".join(ch.lower() if ch.isalnum() else " " for ch in query).split())


def relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def fetch_search(job: tuple[int, dict[str, Any], str, int, Path], token: str | None) -> tuple[int, dict[str, Any]]:
    order, mechanic, query, page, output = job
    if output.exists():
        payload = read_json(output)
        source = "checkpoint"
    else:
        response = get_json("/search", {"type": "game", "q": query, "page": page, "size": 100}, token)
        atomic_write(output, response.payload)
        payload = json.loads(response.payload)
        source = "network"
    if payload.get("code") != 0:
        raise RequestFailure(f"API error for search {mechanic['id']}/{query}: {payload.get('msg', 'unknown')}")
    return order, {"mechanic_id": mechanic["id"], "query": query, "page": page, "path": output, "payload": payload, "source": source}


def select_games(mechanic: dict[str, Any], search_records: list[dict[str, Any]], maximum: int) -> tuple[list[dict[str, Any]], int]:
    """First game_id wins, following configured query/page/API ordering."""
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    duplicates = 0
    for record in search_records:
        for item in record["payload"].get("data", {}).get("items", []):
            game = item.get("game") or {}
            game_id = game.get("game_id")
            if not isinstance(game_id, int):
                continue
            if game_id in seen:
                duplicates += 1
                continue
            seen.add(game_id)
            selected.append(game)
            if len(selected) == maximum:
                return selected, duplicates
    return selected, duplicates


def fetch_detail(game: dict[str, Any], root: Path, token: str | None) -> tuple[int, int | None, Path, str | None]:
    game_id = game["game_id"]
    version = game.get("game_version")
    filename = f"{game_id}-{version if version is not None else 'latest'}.json"
    output = root / "data" / "rezona" / "game-details" / filename
    if output.exists():
        read_json(output)
        return game_id, version, output, None
    params: dict[str, Any] = {"game_id": game_id}
    if version is not None:
        params["game_version"] = version
    try:
        response = get_json("/game/detail", params, token)
        payload = json.loads(response.payload)
        if payload.get("code") != 0:
            raise RequestFailure(f"API error: {payload.get('msg', 'unknown')}")
        atomic_write(output, response.payload)
        return game_id, version, output, None
    except RequestFailure as error:
        return game_id, version, output, str(error)


def build_jobs(mechanics: list[dict[str, Any]], root: Path) -> list[tuple[int, dict[str, Any], str, int, Path]]:
    jobs = []
    order = 0
    for mechanic in mechanics:
        for query in mechanic["queries"]:
            for page in (1, 2):
                path = root / "data" / "rezona" / "search" / mechanic["id"] / query_slug(query) / f"page-{page}.json"
                jobs.append((order, mechanic, query, page, path))
                order += 1
    return jobs


def collect(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    catalog = read_json(root / args.catalog)
    mechanics = catalog["mechanics"]
    if args.pilot:
        mechanics = [entry for entry in mechanics if entry["id"] in PILOT_IDS]
    if len(mechanics) != (12 if args.pilot else 100):
        raise ValueError("mechanics.json does not contain the expected selected mechanics")
    token = load_access_token(root / args.token_file)
    jobs = build_jobs(mechanics, root)
    print(f"Collecting {len(mechanics)} mechanics, {len(jobs)} search pages; token={'configured' if token else 'not configured'}.")
    search_by_mechanic: dict[str, list[dict[str, Any]]] = {entry["id"]: [] for entry in mechanics}
    failures: list[dict[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_search, job, token) for job in jobs]
        records: list[tuple[int, dict[str, Any]]] = []
        for future in concurrent.futures.as_completed(futures):
            try:
                records.append(future.result())
            except RequestFailure as error:
                failures.append({"stage": "search", "error": str(error)})
    for _, record in sorted(records, key=lambda item: item[0]):
        search_by_mechanic[record["mechanic_id"]].append(record)

    output_mechanics = []
    unique_games: dict[tuple[int, int | None], dict[str, Any]] = {}
    maximum = catalog["selection"]["max_games_per_mechanic"]
    for mechanic in mechanics:
        selected, duplicates = select_games(mechanic, search_by_mechanic[mechanic["id"]], maximum)
        for game in selected:
            unique_games[(game["game_id"], game.get("game_version"))] = game
        output_mechanics.append({
            "id": mechanic["id"], "name": mechanic["name"], "queries": mechanic["queries"],
            "searches": [{"query": record["query"], "page": record["page"], "path": relative(record["path"], root),
                          "returned": len(record["payload"].get("data", {}).get("items", [])),
                          "total": record["payload"].get("data", {}).get("total")} for record in search_by_mechanic[mechanic["id"]]],
            "selected_game_ids": [game["game_id"] for game in selected], "selected_count": len(selected),
            "candidate_duplicates": duplicates, "shortfall": max(0, maximum - len(selected)),
        })

    detail_paths: dict[tuple[int, int | None], str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_detail, game, root, token) for game in unique_games.values()]
        for future in concurrent.futures.as_completed(futures):
            game_id, version, path, error = future.result()
            if error:
                failures.append({"stage": "detail", "game_id": str(game_id), "error": error})
            else:
                detail_paths[(game_id, version)] = relative(path, root)
    for record in output_mechanics:
        record["detail_paths"] = {str(game_id): next((path for (candidate_id, _), path in detail_paths.items() if candidate_id == game_id), None)
                                  for game_id in record["selected_game_ids"]}

    index = {
        "catalog_version": catalog["version"], "collection_mode": "pilot" if args.pilot else "full",
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "api_root": API_ROOT,
        "selection": catalog["selection"], "mechanics": output_mechanics,
        "unique_detail_games": len(detail_paths), "failures": failures,
    }
    index_path = root / "data" / "rezona" / "index.json"
    atomic_write(index_path, (json.dumps(index, indent=2, ensure_ascii=False) + "\n").encode())
    print(f"Wrote {relative(index_path, root)}; details={len(detail_paths)} failures={len(failures)}")
    return 1 if failures else 0


def validate(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    index_path = root / "data" / "rezona" / "index.json"
    if not index_path.exists():
        print(f"Validation unavailable: collection index not written yet: {relative(index_path, root)}", file=sys.stderr)
        return 1
    index = read_json(index_path)
    problems = []
    for mechanic in index["mechanics"]:
        ids = mechanic["selected_game_ids"]
        if len(ids) != len(set(ids)):
            problems.append(f"duplicate selected ID in {mechanic['id']}")
        for search in mechanic["searches"]:
            try:
                read_json(root / search["path"])
            except (OSError, json.JSONDecodeError):
                problems.append(f"invalid search payload {search['path']}")
        for game_id, detail_path in mechanic["detail_paths"].items():
            if detail_path is None:
                problems.append(f"missing detail path for {mechanic['id']}/{game_id}")
                continue
            try:
                read_json(root / detail_path)
            except (OSError, json.JSONDecodeError):
                problems.append(f"invalid detail payload {detail_path}")
    if problems:
        print("Validation failed:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    print(f"Validation passed for {len(index['mechanics'])} mechanics and {index['unique_detail_games']} detail files.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path, default=Path("mechanics.json"))
    parser.add_argument("--token-file", type=Path, default=Path(".rezona.local.env"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pilot", action="store_true", help="collect the 12-mechanic pilot")
    mode.add_argument("--full", action="store_true", help="collect all 100 mechanics")
    mode.add_argument("--validate", action="store_true", help="validate data/rezona/index.json")
    args = parser.parse_args()
    return validate(args) if args.validate else collect(args)


if __name__ == "__main__":
    raise SystemExit(main())
