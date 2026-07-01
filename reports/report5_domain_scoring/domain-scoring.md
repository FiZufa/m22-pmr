# Domain Scoring — PMR V2

Domain scoring takes each HPVD candidate and produces 5 component scores that are fused into a single `answer_probability`. The verdict engine then compares this to `probability_threshold` (default 0.50) to decide ALLOW or ABSTAIN.

## Scoring Dimensions

After removing the dead `completeness_score` (was always 0.0 at 5% weight), there are 4 active dimensions plus the confidence sub-system:

| Dimension | Weight | Code | What it measures | Effective influence |
|-----------|--------|------|------------------|-------------------|
| semantic | 0.35 | `semantic_score` | Cross-encoder relevance (query vs candidate_text) | 0.395 (35% + 30% of confidence at 15%) |
| department | 0.20 | `department_score` | Department match (same/related/unrelated) | 0.20 (always 0.0 when dept is None) |
| tenant | 0.15 | `tenant_score` | Tenant ownership (same/global/other) | 0.15 (always 0.6 for global products) |
| trust | 0.10 | `trust_score` | Source type reputation | 0.10 (always 0.85 for product_catalog) |
| confidence | 0.20 | `confidence_score` | Retrieval signal quality (RRF/BM25/vector/semantic) | 0.20 (only dimension with real variance) |

### semantic_score

Computed by `app/pmr/engine/v2/semantic.py` via cross-encoder. The `candidate_text` is constructed in `app/pmr/bridge.py` from `title + brand + description` fields. Scores are sigmoid-normalized to [0.0, 1.0].

**Current limitation:** The `contents` field (rich product descriptions) is not included in `candidate_text`, which could improve semantic matching.

### department_score

Defined in `app/pmr/engine/v2/scoring.py:compute_department_score()`:

- `candidate.dept == current_dept` → 1.0
- Related pair → 0.6
- Otherwise → 0.0

**Current limitation:** Returns 0.0 for all candidates when `department` is None (our eval setup), contributing nothing to discrimination.

### tenant_score

Defined in `app/pmr/engine/v2/scoring.py:compute_tenant_score()`:

- `candidate.tenant_id == current_tenant_id` → 1.0
- `candidate.tenant_id == "global"` → 0.6
- Otherwise → 0.0

**Current limitation:** All Mister Worker candidates have `tenant_id="global"`, so every candidate gets a constant 0.6. No discrimination.

### trust_score

Defined in `app/pmr/engine/v2/scoring.py:compute_trust_score()` using the `source_trust` table in `app/pmr/config/v2_defaults.py`:

- `product_catalog` → 0.85
- `official_policy` → 1.0
- `chat_transcript` → 0.3
- Others → 0.5

**Current limitation:** All candidates have `source_type="product_catalog"`, so every candidate gets a constant 0.85. No discrimination.

### confidence_score

Defined in `app/pmr/engine/v2/confidence.py`. Weighted sum of 4 retrieval signals:

```
confidence = 0.25 × rrf_score
           + 0.20 × normalize(bm25_score, max=20.0)
           + 0.25 × vector_score
           + 0.30 × semantic_score
```

Clamped to [0.0, 1.0]. This is the only dimension with real variance per-candidate.

## Fusion Formula

```python
answer_probability = 0.35 × semantic_score
                   + 0.20 × department_score
                   + 0.15 × tenant_score
                   + 0.10 × trust_score
                   + 0.20 × confidence_score
```

Code: `app/pmr/engine/v2/fusion.py:compute_answer_probability()`

## Dilution Analysis

Because semantic_score feeds into both the semantic weight (0.35) AND 30% of confidence_score (which has weight 0.20), the effective semantic weight is:

```
effective_semantic = 0.35 + (0.30 × 0.20) = 0.395
```

Meanwhile, BM25 — the most direct keyword relevance signal — has only:

```
effective_bm25 = 0.20 (confidence weight) × 0.20 (bm25's share of confidence) = 0.04
```

Three constant-value scores (tenant 0.6 × 0.15, trust 0.85 × 0.10, dept 0.0 × 0.20) account for **0.09 + 0.085 + 0.0 = 0.175** of the probability — ~17.5% of the final score is static metadata noise.

## Known Limitations

1. **Completeness removed** — was always 0.0, dead code eliminated.
2. **Department always None** — `compute_department_score` returns `unrelated` (0.0) when dept is None, which is the common case.
3. **Semantic double-counting** — semantic_score contributes to both the 0.35 direct weight and 30% of confidence_score for a total effective semantic influence of 0.395.
4. **BM25 underweighted** — at 4% effective influence, the most direct keyword match signal is barely heard.
5. **All product candidates look the same** to department/tenant/trust scoring — these only differentiate across source types or multi-tenant setups, not within a single product catalog query.

## Related Files

| File | Role |
|------|------|
| `app/pmr/config/v2_defaults.py` | Weights, thresholds, trust table |
| `app/pmr/engine/v2/scoring.py` | department, tenant, trust scoring |
| `app/pmr/engine/v2/confidence.py` | 4-signal confidence fusion |
| `app/pmr/engine/v2/fusion.py` | Linear weighted sum |
| `app/pmr/engine/v2/gate.py` | Semantic gate |
| `app/pmr/engine/v2/semantic.py` | Cross-encoder reranking |
| `app/pmr/bridge.py` | HPVD → PMR translation, builds candidate_text |
| `app/pmr/core/models.py` | HPVDCandidate, ScoredCandidate |
| `scripts/eval_pmr.py` | Evaluation harness |
