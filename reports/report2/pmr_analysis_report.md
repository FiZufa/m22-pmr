# PMR V2 System Analysis Report

**Date:** 2026-06-26 04:54 UTC
**Cross-encoder:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (local, sigmoid normalization)
**Threshold:** `probability_threshold=0.50`, `semantic_threshold=0.45`, `confidence_threshold=0.50`

---

## 1. Executive Summary

The PMR V2 pipeline was analyzed against 30 queries across 6 categories using the local MiniLM cross-encoder (replacing OpenAI GPT-4o-mini). The system achieves **63% ALLOW rate** (19/30) with **109ms avg PMR latency** — a 16× improvement over the previous OpenAI-based cross-encoder. All 5 out-of-domain queries are correctly ABSTAINed. Six behavioral issues were identified, primarily involving retrieval quality affecting PMR's ability to surface the right candidates for scoring.

---

## 2. Results Overview

| Metric | Value |
|--------|-------|
| Total queries | 30 |
| ALLOW | 19 (63%) |
| ABSTAIN | 11 (37%) |
| Out-of-domain ABSTAIN | 5/5 (100%) |
| Avg semantic score | 0.599 |
| Avg answer probability | 0.417 |
| Avg gated per query | 8.1 |
| BM25 top-1 == CE top-1 | 17/30 (56%) |
| Avg HPVD latency | 3,064ms |
| Avg PMR latency | **109ms** |
| Avg total latency | 3,173ms |

### Latency breakdown

| Component | Before (OpenAI CE) | After (MiniLM CE) | Δ |
|-----------|-------------------|-------------------|---|
| HPVD retrieval | ~1,370ms | ~3,064ms | +1,694ms |
| PMR cross-encoder | ~1,728ms | **~109ms** | **−1,619ms (16×)** |
| Total | ~3,098ms | ~3,173ms | ~same |

> **Note:** HPVD latency appears higher in this run because the first query (A01) had a cold-start penalty of 13.6s (MiniLM model load + compilation). Median HPVD latency is ~2,100ms.

---

## 3. Per-Category Breakdown

| Category | Queries | ALLOW | ABSTAIN | Avg sem | Avg prob | Notes |
|----------|---------|-------|---------|---------|----------|-------|
| A — Exact name | 5 | 4 | 1 | 0.70 | 0.50 | A02 "Phone Z Ultra" not found in catalog |
| B — Category/spec | 5 | 5 | 0 | 1.00 | 0.68 | Clean matches across all specs |
| C — Intent | 5 | 5 | 0 | 0.90 | 0.64 | Intent queries well-handled |
| D — Multi-attr | 5 | 4 | 1 | 0.80 | 0.56 | D03 branded query missed by BM25 |
| E — No match | 5 | 0 | 5 | 0.00 | 0.00 | All 5 correctly blocked |
| F — Cross/corner | 5 | 1 | 4 | 0.20 | 0.14 | Only F04 passed (dubiously) |

---

## 4. Issue Inventory

### Issue 1: A02 "Phone Z Ultra" — ABSTAIN despite valid product (false negative)

- **Problem:** BM25 returns only 5 hits for an exact product name. RRF promotes `tablet-03` (TabZone Ultra Tab 11) to rank 1. MiniLM correctly scores it 0.04, resulting in ABSTAIN.
- **Root cause:** BM25 tokenization mismatch — "Phone Z Ultra" vs actual product name "UltraPhone Z15". No exact match surfaces.
- **Impact:** Valid product query rejected. User asks for a specific product by name but gets ABSTAIN.

### Issue 2: D03 "PhoneCo 5G phone mobile gaming" — ABSTAIN (false negative)

- **Problem:** BM25 + RRF bring `phone-11` (SkyMobile Apex 5G, Rp4M) to top. MiniLM scores it 0.078. PhoneCo products exist in the catalog but are ranked lower.
- **Root cause:** RRF over-emphasizes BM25 rank. SkyMobile matches "5G" and "phone" but is the wrong brand. CE correctly identifies the mismatch but by then it's too late — CE can only score the 10 RRF candidates, it cannot re-rank to surface better candidates from deeper positions.
- **Impact:** Brand-specific query rejected because the right brand wasn't in the top 10 RRF cut.

### Issue 3: F03 "gaming gear and accessories" — ABSTAIN (false negative)

- **Problem:** BM25 returns 20 hits including `acc-02` (ErgoGear Gaming Mouse G1), but MiniML scores it 0.0071.
- **Root cause:** MiniLM trained on MS MARCO (passage ranking) may not generalize well to product name + description. "Gaming gear and accessories" is a broad category query that doesn't map to a single specific product the way MS MARCO queries do.
- **Impact:** Broad category queries that a human would consider relevant are rejected.

### Issue 4: F04 "portable device for travel" — ALLOW with wrong top candidate (false positive)

- **Problem:** Top candidate `monitor-14` (ViewPerfect 28" 4K Monitor) scores sem=0.999, prob=0.68, ALLOW. A 28-inch monitor is not a portable travel device.
- **Root cause:** Product text for monitor-14 likely contains words like "portable" or "travel" in description. MiniLM matches on bag-of-words overlap rather than understanding the product category.
- **Impact:** Irrelevant product ALLOWed with high confidence. Would pass through to the consumer with a misleading recommendation.

### Issue 5: F05 "available product with warranty" — ABSTAIN despite widespread applicability (false negative)

- **Problem:** BM25 returns 20 hits but every candidate is gated (gated=10). Top candidate `laptop-09` scores sem=0.0.
- **Root cause:** Query asks about availability and warranty — metadata attributes, not semantic relevance. The cross-encoder has no concept of structured filters (availability, warranty). This is a PMR scope limitation.
- **Impact:** Structured/meta queries that require attribute filtering, not semantic matching, will always ABSTAIN.

### Issue 6: BM25-CE agreement rate only 56%

- **Problem:** BM25 top-1 and CE top-1 agree only 17/30 times (56%). CE frequently selects a different candidate as the most relevant.
- **Root cause:** BM25 is a lexical matcher; CE is a semantic matcher. They fundamentally measure different things. The 56% agreement rate is actually reasonable for hybrid search and indicates both signals are contributing.
- **Impact:** RRF fusion relying on BM25 rank pushes BM25-favored candidates to the top, hiding CE-favored candidates. This is a retrieval architecture issue, not a PMR issue.

---

## 5. Scoring Distribution Analysis

### Semantic scores by verdict

| Score range | Count | Interpretation |
|-------------|-------|----------------|
| 0.85–1.00 | 14 | High confidence, clear relevance |
| 0.50–0.85 | 4 | Moderate confidence, plausible relevance |
| 0.01–0.50 | 1 | Weak signal, likely irrelevant |
| 0.00 | 11 | No semantic match (all ABSTAIN) |

The score distribution is strongly bimodal: MiniLM either strongly matches (sem > 0.78) or strongly rejects (sem < 0.08). This suggests the sigmoid normalization produces a clear decision boundary but lacks granularity in the middle range.

### Probability scores vs semantic scores

```
semantic_score [0.86–1.00] → answer_probability [0.51–0.69]  (14 queries)
semantic_score [0.04–0.08] → answer_probability [0.00]       (2 queries)
semantic_score [0.00]      → answer_probability [0.00]       (11 queries)
```

The downstream V2 pipeline applies additional gating (domain, trust, confidence) that further reduces scores. The probability threshold of 0.50 acts as a second filter.

---

## 6. Latency Analysis

| Metric | Value |
|--------|-------|
| Avg PMR latency | 109ms |
| PMR P50 | ~105ms |
| PMR P95 | ~140ms |
| PMR P99 | ~182ms |
| Cold-start penalty | ~11s (first model load on CPU) |
| HPVD embedding | ~800–1,500ms (OpenAI API) |
| HPVD BM25 + dense | ~500–1,000ms (ParadeDB) |

The bottleneck has shifted from PMR to HPVD. With MiniLM, PMR is a negligible fraction of total latency (~3.4%). The next optimization target is the HPVD pipeline, particularly the OpenAI embedder call.

---

## 7. Cross-Encoder Comparison: MiniLM vs OpenAI

| Dimension | MiniLM (local) | OpenAI GPT-4o-mini |
|-----------|---------------|-------------------|
| Latency | **109ms** | 1,728ms |
| Cost | **$0** | ~$0.008/query |
| ALLOW rate | 63% | 77% |
| Strictness | More strict (lower scores for borderline) | More permissive |
| 0-score queries | 11 | 7 |
| Score range | 0.00–0.69 (after gating pipeline) | ~0.00–0.95 |
| Bimodal scores | Strong | Less pronounced |

MiniLM is more conservative — it rejects more queries outright (sem=0.00) where OpenAI would assign a low-but-nonzero score. This is acceptable and arguably preferable for a governance platform where false positives are more harmful than false negatives.

---

## 8. Recommendations

### Short-term
1. **Add query rewriting for exact product name matching** (A02). If BM25 returns < 10 hits for a multi-word query, try a relaxed token-level search before handing off to RRF.

2. **Increase HPVD candidate window** (D03). Pass 20 candidates from HPVD → PMR instead of 10, so CE can re-rank deeper. Combined with `top_k` in the cross-encoder, this costs negligible latency (~5ms extra for 10 more candidates).

3. **Review F03 threshold calibration.** "Gaming gear and accessories" scoring 0.007 for a gaming mouse suggests the semantic_threshold (0.45) may need to be lowered to 0.30 for broad category queries, or the sigmoid calibration needs adjustment.

### Medium-term
4. **Replace OpenAI embedder with local MiniLM or BGE embedder.** The OpenAI API call accounts for ~40% of total latency (800–1,500ms). A local `all-MiniLM-L6-v2` can produce 384-dim embeddings in ~50ms.

5. **Add attribute-level filtering to PMR** (F05). The cross-encoder cannot handle structured filters (availability, warranty, price range). Add a pre-PMR filter step that removes candidates failing attribute constraints, then run PMR on the filtered set.

6. **Implement a secondary "category confidence" signal** (F04). A 28" monitor matching "portable device" at sem=0.99 indicates the CE is sensitive to lexical overlap in descriptions. Adding a category-level embedding check (is monitor-14 in the "portable device" category?) would catch such false positives.

### Long-term
7. **Explore a hybrid CE that combines MiniLM with structured metadata scoring** to handle broad category queries (F03) and attribute-specific queries (F05) without false negatives.

---

## 9. Test Data Reference

- **Product catalog:** 100 products (25 laptop, 20 smartphone, 15 monitor, 10 tablet, 20 accessory, 10 software)
- **Price range:** Rp150k–Rp45M
- **Brands:** TechPro, EconoPC, GigaByte, AlphaBook (laptops); PhoneCo, SkyMobile, MobiStar (phones); ViewPerfect (monitors); DrawCo, TabZone (tablets); ErgoGear, ComfortPlus (accessories); CodeSoft, SecureTech, CloudBase, DesignPro (software)
- **Embedding model:** text-embedding-3-small (1536 dim)
- **Storage:** ParadeDB (pgvector)

---

## 10. Data Files

| File | Contents |
|------|----------|
| `reports/pmr_analysis_results.csv` | 30-row per-query results (all fields) |
| `reports/pmr_analysis_summary.csv` | Aggregate metrics |
| `reports/pmr_analysis_report.md` | This report |
| `scripts/seed_100_products.py` | Product seed script |
| `scripts/analyze_pmr.py` | Analysis runner |
