# Rezona viral-mechanics corpus

## Purpose

Create a reproducible archive of Rezona search and game-detail responses for up to 100 games across each of 100 viral or culturally recognizable mechanics. Selection preserves the API's returned order; reported counters are intentionally not used for ranking.

## 2026-08-14 — Endpoint and pilot preparation

- Confirmed `GET https://api.rezona.ai/api/v3/search?type=game&q=<query>&page=<1|2>&size=100` is public, returns JSON, and is capped at 200 results per query.
- Confirmed public `GET /api/v3/game/detail?game_id=<id>&game_version=<version>` returns individual game metadata. The collector can send a temporary bearer token when available and retries anonymously if needed.
- The catalog begins with a 12-mechanic pilot: parkour/obby, endless runner, clicker, idle tycoon, merge, match-3, tower defense, survival crafting, racing, dress-up, rhythm, and social deduction.
- The full catalog has 100 mechanics. Each has ordered generic, synonym, and mechanically relevant franchise queries. Query order and then API item order determine which 100 unique game IDs are selected.

## Secret handling and renewal

The token file is local and ignored by Git. Never put token values, cookies, authorization headers, or browser-network exports in this journal, generated JSON, commits, or a README.

To renew a token: sign in at https://create.rezona.ai/login, reach the workspace, inspect an authenticated Rezona API request in browser developer tools, copy the new access token into `.rezona.local.env`, and rerun the collector. Replace or revoke the old temporary token afterward.

## Operational record

The collector writes raw search responses, deduplicated game-detail responses, and `data/rezona/index.json`. It uses two concurrent requests, retries transient failures with backoff, and checkpoints every successful file. Add an entry here after the pilot and after the full run with coverage, retries, shortfalls, and validation results.

## 2026-08-14 — Pilot complete

- Collected all 72 search pages for the 12-mechanic pilot (three ordered queries × two 100-result pages per mechanic).
- Selected 100 unique games for every pilot mechanic. No mechanic had a shortfall and no duplicate game ID appeared within a mechanic's selected set.
- Saved 1,193 globally unique game-detail payloads. The difference from 1,200 memberships is expected cross-mechanic overlap.
- The collector reported zero request failures. Local integrity validation passed for all 12 mechanics, all search payloads, and all detail payloads.
- The full run remains intentionally manual: `python3 tools/collect_rezona_corpus.py --full`. It resumes from existing raw files and writes a new index after completion.

## 2026-08-14 — Full collection started

- Started `python3 tools/collect_rezona_corpus.py --full` after the validated pilot. Existing pilot search and detail files are used as checkpoints.
- The final `data/rezona/index.json` is written only when the full run completes. Before then, file counts under `data/rezona/search/` and `data/rezona/game-details/` are the resumable progress record.

## 2026-08-15 — Full collection complete

- Archived all 600 configured search responses (100 mechanics × 3 queries × 2 pages).
- Every mechanic selected exactly 100 game memberships: 10,000 memberships total, zero shortfalls, and no within-mechanic duplicate selected IDs.
- Archived 8,528 globally deduplicated game-detail JSON responses. The difference from the membership total is expected cross-mechanic reuse.
- The final index reports zero collection failures. `python3 tools/collect_rezona_corpus.py --validate` passed for all 100 mechanics and all 8,528 detail files; the collector unit tests also passed.
- A future concise README can cite this journal and the collector command without reproducing local token values.

## 2026-08-15 — Enriched aggregate complete

- Generated `data/rezona/games.enriched.json`: one deduplicated record per game/version, embedding each detail payload's `data` object.
- Each record adds mechanic tags, observed query tags, and ordered provenance records pointing to the saved search file, page, item position, and mechanic selection rank.
- The aggregate contains 8,528 games and 10,000 mechanic memberships. Validation confirmed every embedded detail object matches its source payload and every provenance record points to the referenced saved-search item.
- The enriched file is generated data and remains Git-ignored with the raw archive; it contains no local authentication material.

## 2026-08-15 — Open-source publication preparation

- Prepared the repository for public release as `hassanvfx/rezona-api`, with the enriched aggregate selected as the tracked public dataset and the 83 MB raw search/detail archive retained locally and ignored.
- Added a SHA-256 manifest for `data/rezona/games.enriched.json`; the public artifact is 16,968,647 bytes and preserves 8,528 game records and 10,000 provenance memberships.
- Added an author-provided historical disclosure record under `docs/disclosure/`. The public documentation attributes it as historical context, does not independently verify its estimates or opinions, and does not treat technical accessibility as a legal conclusion about data rights.
- Added a source-data notice with a correction/removal process. Original repository code, documentation, diagrams, and generated artwork are MIT-licensed; third-party game data and related rights are explicitly excluded.
- GitHub remote creation and GitHub Pages activation remain pending valid GitHub authentication for the target account.

## 2026-08-15 — Project header refresh

- Replaced the project header with original generated artwork informed by a visual review of `rezona.ai`: black high-contrast space, energetic game-card collage, and bright social-game accents. No Rezona source artwork, logo, text, or recognizable characters were copied into the new asset.
- Refreshed the selected banner with GPT Image 2 and added the independent in-art label `REZONA API` / `by hassanvfx`; the Pages layout keeps an equivalent screen-reader heading and avoids a duplicate visible title.

## 2026-08-15 — API reference and local credential guidance

- Expanded the public README with a bounded map of confirmed API families and a link to the detailed reconstruction record, retaining explicit confirmed/inferred/open status rather than presenting the surface as complete.
- Added token-renewal instructions for a user's own authenticated session. The documented workflow stores only `REZONA_ACCESS_TOKEN` in ignored `.rezona.local.env`; it excludes cookies, browser exports, and token values from the repository and generated artifacts.

## 2026-08-15 — Disclosure claim-context expansion

- Expanded README context for the disclosure's historical 120M+ game-count and per-game-cost questions. The text explicitly treats them as author-attributed hypotheses, explains why query search is not a platform census, and records that the corpus does not audit pricing, total spend, or a global inventory.

## 2026-08-15 — GitHub Pages narrative expansion

- Expanded the GitHub Pages overview to carry the README's motivation, historical-claim context, evidence boundaries, API-reconstruction scope, provenance method, and local-token safety guidance in a navigable presentation.
- Verified the updated static page at desktop and 390px mobile widths with all narrative sections present and no horizontal overflow.

## 2026-08-15 — Search coverage lower bound and cost scenarios

- Added a deterministic search-coverage analyzer that merges repeated literal query terms, unions observed game IDs from all saved search pages, measures overlap, and writes a tracked JSON snapshot.
- The August 15 snapshot has 300 configured probes, 290 distinct query terms, 600 saved pages, 32,238 observed unique game IDs, 54,200 term memberships, 80.13% single-term IDs, and 264 terms at the API's 200-result ceiling.
- Published 32,238 only as an observed raw-search lower bound. The report explains why curated, capped query windows do not support a numeric searchable-lake or platform-total extrapolation, and documents requirements for a future estimator.
- Added $1/$10 arithmetic scenarios per completed indexed game. They are explicitly not audited pricing, platform spend, or a claim about failed attempts and non-generation costs.

## 2026-08-15 — Narrative and visual evidence refresh

- Reframed the README and GitHub Pages overview around the reproducible 32,238-ID lower bound, with the explicit non-census caveat in the opening statement.
- Added a short question → receipts → limits narrative and an original text-free evidence-map illustration. It visualizes provenance flow only; it contains no Rezona source artwork, logos, characters, credentials, or source payloads.
- Retained the historical 120M claim solely as attributed context. The refreshed public copy continues to distinguish observed data from platform-wide count, pricing, spend, rights, or legal conclusions.

## 2026-08-15 — Claim, token-cost, and overlap sensitivity refresh

- Reframed the public opening around the disclosure-attributed historical 120M+ claim and the conditional $120M/$1.2B arithmetic at $1/$10 per completed game. It remains explicitly separate from verified Rezona spend, inventory, provider, workflow, or legal conclusions.
- Added dated public token-price benchmarks for GPT-5.6 Terra ($2.50/M input, $15/M output) and GPT-5.6 Sol ($5/M input, $30/M output) as transparent examples of how multi-request reasoning workflows can approach the scenario brackets. They are reference models only, not evidence of Rezona's usage.
- Extended the coverage analyzer with the visible incidence inputs: 25,831 IDs observed in one merged term (`f1`) and 3,602 in two (`f2`). The simple incidence/Chao2 expression `32,238 + f1² / (2 × f2)` yields 124,859.
- Published 124,859 only as an overlap-only sensitivity. Curated terms, opaque/dependent ranking, and the 264/290 result caps violate the assumptions needed to treat it as an inventory or searchable-lake estimate.

## 2026-08-15 — Keyword-space discovery pilot

- Added a separate adaptive keyword-space collector that draws a fixed 60-query frame from long-tail unigram and bigram vocabulary in the existing enriched game-title corpus. It is a diversity-expansion method, not a probability sample or data-lake estimate.
- Archived 120 search pages (two pages per query): 11,341 returned items, with 108 pages reporting the API's 200-result ceiling.
- The search windows exposed 9,102 game IDs not present in the original enriched corpus. Detail capture was deliberately capped at the first 2,000 newly observed IDs in deterministic query/page/API order; all 2,000 detail responses were valid.
- Raw keyword-space sources remain local and Git-ignored. The public summary records only aggregate counts and the method; it contains no credentials, cookies, authorization values, or raw payloads.
# Expanded corpus and combined-search evidence — 2026-08-15

- Merged the deterministic keyword-space pilot into `data/rezona/games.enriched.json`.
  The public detail corpus now has 10,528 unique game/version records: 10,000
  mechanics-led memberships and 2,000 keyword-space memberships (12,000 provenance
  entries). Raw captures remain local and ignored.
- Extended record tags and provenance with collection ID and discovery method; pilot
  records retain keyword query, unigram/bigram stratum, page, item position, rank, and
  raw-path provenance even where no mechanic tag applies.
- Combined the 290-term mechanics frame with the 60-term keyword pilot: 350 merged
  literal terms, 720 pages, 65,541 memberships, and 40,026 observed IDs. The pilot
  added 7,788 IDs beyond the original raw-search union.
- Published 156,988 only as an exploratory adaptive-search overlap estimate of
  searchable-result diversity (`40,026 + 31,947² / (2 × 4,363)`). It is explicitly
  not a verified inventory, actual data lake, platform census, or confidence interval.
  The 318/350 capped-term count and stress-test outputs are published to show model
  sensitivity rather than imply certainty.
- Regenerated `docs/data/search-coverage-analysis.json` and the tracked dataset
  manifest. New enriched-dataset SHA-256:
  `1f57b4116658341ffd0c6be194e202877e8cc0ec2709adc92f8f5bfa439c5a6a`.
