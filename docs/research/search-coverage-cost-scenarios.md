# Claim, cost, and expanded search-overlap analysis

## The claim this analysis examines

An author-provided historical disclosure attributes a **“120M+” meme-games**
marketing claim to Rezona. If that count meant completed games, then simple
per-completed-game scenarios imply **$120M at $1/game** or **$1.2B at $10/game**.

That is conditional arithmetic—not evidence of Rezona's actual spend, model supplier,
generation workflow, platform inventory, or legal status of any source data. The
disclosure is historical context, not independent verification of the claim.

## What the archive directly observed

The combined saved-search archive demonstrates **40,026 unique game IDs** in its query
windows. This merges the original mechanics archive (32,238 IDs) with a fixed-seed
60-query title-keyword pilot that added **7,788 IDs beyond the original raw union**.
It is a reproducible lower bound, not a platform census or searchable-lake estimate.

| Metric | Result |
| --- | ---: |
| Configured query probes | 360 |
| Distinct literal query terms after merge | 350 |
| Saved search pages | 720 |
| Unique IDs observed across query windows | 40,026 |
| Term memberships after per-term deduplication | 65,541 |
| IDs observed in one term (`f1`) | 31,947 (79.82%) |
| IDs observed in two terms (`f2`) | 4,363 |
| Median pairwise term intersection | 0 |
| Mean pairwise Jaccard similarity | 3.30% |
| Terms at the 200-result ceiling | 318 / 350 |

Machine-readable snapshot: [`../data/search-coverage-analysis.json`](../data/search-coverage-analysis.json).

## Why $1 and $10 can both be plausible scenarios

The figures are deliberately scenario brackets per **completed indexed game**. They
exclude failed generations, retries, hosting, moderation, storage, licensing,
support, and all other non-token costs. They do not describe Rezona's implementation.

As a transparent benchmark, current official OpenAI documentation listed the following
standard token prices when this note was updated (2026-08-15):

| Reference model | Input / 1M tokens | Output / 1M tokens | Why it is relevant |
| --- | ---: | ---: | --- |
| [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) | $2.50 | $15.00 | Frontier reasoning model positioned for balanced cost and capability. |
| [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol) | $5.00 | $30.00 | Frontier reasoning model positioned for complex professional work. |

For a reasoning workflow, the reference formula is:

```text
per-game token cost = input tokens × input rate + output/reasoning tokens × output rate
```

Reasoning tokens are part of reported output-token usage in the Responses API. A game
builder may use multiple requests for planning, implementation, debugging, and
revision; the examples below therefore represent **aggregate multi-request budgets**,
not one API call or a claim about any particular product.

| Benchmark | Approx. $1 aggregate budget | Approx. $10 aggregate budget |
| --- | --- | --- |
| GPT-5.6 Terra | 10k input + 65k output/reasoning = $1.00 | 100k input + 650k output/reasoning = $10.00 |
| GPT-5.6 Sol | 10k input + 31.7k output/reasoning = $1.00 | 100k input + 316.7k output/reasoning = $10.00 |

Prices can change, and actual costs depend on provider, model, caching, batch pricing,
tool calls, image/video generation, retries, and token budgets. The table demonstrates
why the two brackets are technically conceivable; it does not establish that either
one was Rezona's cost.

## Exploratory overlap model: how the 156,988 number is derived

Query overlap can be used in ecology-style incidence estimators to ask a narrow
question: given how often IDs appeared once or twice across query terms, how many
distinct IDs might be suggested under comparable sampling conditions?

Using the simple incidence/Chao2 sensitivity form:

```text
S = S_obs + f1² / (2 × f2)
  = 40,026 + 31,947² / (2 × 4,363)
  = 156,988
```

This **156,988** result is an **exploratory adaptive-search overlap estimate of
searchable-result diversity**, not Rezona's verified inventory, actual data lake,
platform census, or a confidence interval. It is included to make overlap visible,
not to convert it into a claim.

The inference assumptions fail in this archive:

1. Terms were curated for mechanics, synonyms, and franchises—not randomly sampled
   from a representative query vocabulary.
2. **318 of 350** terms hit a 200-result cap, hiding unknown result tails.
3. Related terms and opaque ranking create dependent, non-comparable detection events.
4. Search behavior, private inventory, identity handling, and collection time can all
   affect what appears.

Low overlap still has a useful operational meaning: it shows that the curated terms
found many different visible result neighborhoods, so additional carefully documented
probes may discover more records. It does not justify publishing a platform-total
range from this snapshot.

### Assumption stress test — not confidence intervals

| Model frame | Terms | Observed IDs | Chao2-style output | Meaning |
| --- | ---: | ---: | ---: | --- |
| Original mechanics frame | 290 | 32,238 | 124,859 | Earlier adaptive curated frame. |
| Combined frame | 350 | 40,026 | 156,988 | Primary exploratory model output. |
| Uncapped-only subset | 32 | 2,555 | 31,741 | Restricted subset; demonstrates frame sensitivity. |

The variation is the finding: these dependent, capped query frames do not support a
single inventory claim.

## Cost scenarios at each scale

| Scenario | Game count | At $1/game | At $10/game | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Original curated corpus | 8,528 | $8,528 | $85,280 | Selected mechanics-led corpus; not a total. |
| Expanded enriched corpus | 10,528 | $10,528 | $105,280 | Includes the 2,000 keyword-pilot details. |
| Combined observed lower bound | 40,026 | $40,026 | $400,260 | Unique IDs in saved query windows; not a census. |
| Exploratory overlap model | 156,988 | $156,988 | $1,569,880 | Assumption-dependent model output; not an inventory estimate. |
| Historical 120M comparison | 120,000,000 | $120,000,000 | $1,200,000,000 | Attributed historical comparison; not a project finding. |

## Reproduce

The raw search archive and collection index are intentionally Git-ignored provenance
sources. A clean clone does not contain them. Recollect the raw search pages first,
then run:

```bash
python3 tools/analyze_rezona_search_coverage.py
python3 -m unittest discover -s tests -v
```

The analyzer regenerates the tracked JSON snapshot deterministically. It does not make
network requests and never reads credentials.
