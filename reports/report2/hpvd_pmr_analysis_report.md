# PMR System Analysis Report

**Date:** 2026-06-25
**Data:** 100 products (real OpenAI embeddings) | **Queries:** 30 across 6 categories

---

## Quick Summary

| Metric | Value |
|--------|-------|
| BM25 top-1 == CE top-1 agreement | 60% (18/30) |
| Verdict ALLOW rate | **0% (0/30)** |
| Verdict ABSTAIN rate | 100% (30/30) |
| Avg semantic score (cross-encoder) | 0.740 |
| Avg answer probability (after fusion) | 0.508 |
| Avg gated per query | 6.8 / 10 |
| Avg HPVD latency | 1371ms |
| Avg PMR (cross-encoder) latency | 1728ms |
| Avg total latency | 3099ms |
| Queries with BM25 hits | 93% (28/30) |
| Queries with Dense hits | 100% (30/30) |

---

## Issues Found

### 1. ALL queries ABSTAIN — pipeline never ALLOWs

Current `probability_threshold = 0.75` is too high. Even exact product name matches like "Monitor 4K Gaming" (CE score = 1.0) only reach answer_probability = 0.69. The entire pipeline is **effectively dead** — it never outputs ALLOW.

### 2. Dense search false positive on every query

All 100 products have embeddings, so dense search always returns 20 candidates — even for gibberish like `"zzzzzzzzzzz"` or out-of-domain queries like `"tesla electric car"`. RRF then blindly merges these into 10 candidates regardless of BM25 signal.

### 3. Latency too high for production

| Component | Avg | Bottleneck? |
|-----------|-----|-------------|
| Query embedding (OpenAI) | ~500ms | Yes |
| BM25 + Dense search (sequential) | ~400ms | No (DB bounded) |
| Cross-encoder rerank (GPT-4o-mini) | **1728ms** | **Yes** |
| **Total** | **~3100ms** | **Bad** |

The cross-encoder via GPT-4o-mini accounts for 56% of total latency.

### 4. BM25 and Cross-Encoder disagree 40% of the time

BM25 top-1 matches CE top-1 only 60% of the time. In 12/30 queries, BM25's top candidate differs from the cross-encoder's top pick, indicating room for improvement in the retrieval stage.

### 5. No query reformulation

Current setup uses `PassthroughQueryReformulator` — no synonym expansion, no spelling correction. BM25 relies purely on exact keyword matching.

### 6. First query cold start

First query (A01) took 14s total — 11s HPVD + 3s PMR. Likely cold start in OpenAI calls and DB connection pool.

---

## Recommendations

| # | Recommendation | Expected Impact | Effort |
|---|---------------|-----------------|--------|
| 1 | **Lower probability_threshold to 0.50** in `app/pmr/config/v2_defaults.py` | ~60% of queries should become ALLOW (based on current prob distribution) | Low (1 line) |
| 2 | **Swap cross-encoder to local SentenceTransformer** (`cross-encoder/ms-marco-MiniLM-L-6-v2`) | PMR latency from 1728ms → ~50ms | Medium (new adapter) |
| 3 | **Parallelize sparse + dense search** (needs 2 DB connections) | HPVD latency from 1371ms → ~800ms | Low (asyncio.gather) |
| 4 | **Add BM25 confidence filter** — if BM25 hits = 0, skip dense/RRF or flag uncertainty | Prevents false positive candidates from dense-only retrieval | Low |
| 5 | **Implement query reformulation** (synonym expansion using LLM) | Improve BM25 recall for intent-based queries | Medium |
| 6 | **Prime connection pool** at startup (warm-up query) | Eliminate 14s cold start spike | Low |

### Quick win — just tune threshold

Edit `app/pmr/config/v2_defaults.py` line 17:

```python
"probability_threshold": 0.75,  # before → 0% ALLOW
"probability_threshold": 0.50,  # after  → ~60% ALLOW
```

Then re-run analysis:

```bash
uv run python scripts/analyze_pmr.py
```

### Cost analysis

| Component | Current cost | With SentenceTransformer |
|-----------|-------------|------------------------|
| Query embedding | $0.0001/query | Same (still OpenAI) |
| Cross-encoder | $0.008/query | **$0.00** (local) |
| **Total per query** | **$0.008** | **$0.0001** |
| **Cost for 10k queries** | **$80** | **$1** |

---

## Appendix: Raw Data

- `reports/pmr_analysis_results.csv` — 30 rows, one per query
- `reports/pmr_analysis_summary.csv` — aggregate metrics
