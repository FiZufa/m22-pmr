# ADR 0002: PMR Layer with Cross-Encoder Reranking

Date: June 18, 2026
Status: Proposed

## Problem Statement

The existing HPVD retrieval stage (BM25 + pgvector via RRF) produces a quantitatively good candidate list, but has two weaknesses that need to be addressed:

### 1. Compression Loss (Semantic Compression)

Bi-encoders (embedding models such as `text-embedding-3-small`) work by compressing the entire meaning of a sentence into a single, fixed-dimensional vector (1536 dimensions). This compression process inevitably discards subtle nuances of meaning.

A concrete example in the context of this platform:
- Query: *"AI product that can detect fraudulent online banking transactions without high false positives"*
- The bi-encoder will find products with the general category *"fraud detection"*, but may miss the emphasis on the keyword **"high false positives"**, which is the core of the user's need.
- Vector compression loses relational precision between terms in a sentence.

### 2. Skimming (Shallow Relevance Matching)

The current RRF only considers the ranking position of each channel, not the content depth of the query-document pair. This means:
- Documents that *shallowly* mention many of the query's keywords can receive a high RRF score, even though they are contextually irrelevant.
- There is no mechanism to assess whether the document's content actually answers the query's question.

---

## What is Cross-Encoder? (vs. Bi-Encoder)

| | Bi-Encoder (Current) | Cross-Encoder (Proposed) |
|---|---|---|
| **Input** | `encode(query)`, `encode(doc)` separately | `(query, doc)` evaluated together |
| **Output** | Vector embedding | Direct scalar relevance score |
| **Mechanism** | Cosine similarity between vectors | Attention cross-query ↔ token-by-token |
| **Compression** | Lossy (fixed-dim vector) | Lossless (full token attention) |
| **Latency** | O(1) retrieval after indexing | O(n) — evaluate one by one |
| **Scalability** | Very high (ANN indexing) | Limited — only for *top-k small sets* |
| **Ideal scenario** | First-stage retrieval (thousands of documents) | Second-stage reranking (top 20-50 documents) |

The cross-encoder does not compress documents into vectors. It reads the entire query + document pair at once and produces a much more accurate relevance score. The downside is O(n) latency, so the cross-encoder is only suitable for reranking a small number of candidates, not the entire corpus.

---

## Proposed Architecture: PMR Layer with Cross-Encoder

In the HPVD architecture, the PMR (Probabilistic Model of Relevance) will act as the second layer, receiving the HPVDResult output and generating the final verdict.

### New Pipeline Flow

```
User Queries 
│ 
▼ [ LAYER 1 ] HPVD Kernel (already exists) 
│ ├── QueryReformulator → keyword_query + embedding_query 
│ ├── EmbedderPort → vector[1536] 
│ ├── CandidateStore → sparse_candidates + dense_candidates 
│ └── RRF Scorer → HPVDResult (candidates top-k, e.g. top-20) 
│ 
│ Output: HPVDResult { candidates[20], diagnostics, uncertainty_flags } 
│ 
▼ [ LAYER 2 ] PMR Layer (proposed) 
│ ├── CrossEncoderPort → rerank candidates 
│ │ Input: (raw_query, doc_text) × 20 pairs 
│ │ Output: relevance_score per candidate 
│ │ 
│ ├── PMRScorer → combine rrf_score + cross_encoder_score 
│ │ Strategy: weighted fusion or cascade thresholding 
│ │ 
│ └── ThresholdFilter → filter candidates below threshold 
│ Output: PMRResult { reranked_candidates, verdict: allow/abstain } 
│ 
▼ Consumer Response
```

### PMR Position in Code

PMR is not part of `app/hpvd/`. PMR is a governance layer that will be created in one of two locations:
- `app/domains/products/pmr.py` — if the PMR is product-domain-specific
- `app/pmr/` — if the PMR will be used across domains (products, policies, knowledge, etc.)

Recommendation: **`app/pmr/`** as a standalone module that uses the same Ports & Adapters pattern as HPVD, so that:
1. Other domains (policy engine, knowledge base) can utilize the same PMR.
2. Cross-encoder models can be swapped (via ports) without changing business logic.

---

## Proposed Component Design

### CrossEncoderPort (ABC)

```
CrossEncoderPort interface:
rerank(
query: str,
candidates: list[HPVDCandidate]
) -> list[ScoredCandidate]

# ScoredCandidate = HPVDCandidate + cross_encoder_score: float
```

### Adapter Options (implementation options)

Three concrete options for implementing `CrossEncoderPort`:

#### A. SentenceTransformer Cross-Encoder (Local Model)
- Model: `cross-encoder/ms-marco-MiniLM-L-6-v2` or `cross-encoder/nli-deberta-v3-small`
- Deployment: Self-hosted (CPU/GPU)
- **Pros:** Zero cost per query, no data going out to external APIs, predictable latency.
- **Cons:** Requires deployment infrastructure (model serving), memory/GPU consumption.
- **Suitable if:** This platform is deployed on-premises or where data governance is sensitive.

#### B. Cohere Rerank API
- `cohere.rerank(model="rerank-english-v3.0", ...)`
- **Pros:** No infrastructure, state-of-the-art accuracy, pay-per-use.
- **Con:** Data goes out to Cohere servers, there's network latency, and API fees.
- **Suitable if:** The platform is cloud-native and there are no data sovereignty restrictions.

#### C. OpenAI Reasoning-Based Rerank (LLM Cascade)
- Use GPT-4o-mini to assess relevance (query, doc) with structured output.
- **Pro:** Easy to implement (OpenAI client already exists).
- **Con:** Most expensive (token-based pricing), high latency, less deterministic.
- **Suitable if:** The number of queries is very small and accuracy is an absolute priority.

**Initial recommendation: Option A (SentenceTransformer)** with a port-first architecture so it can be switched to Option B (Cohere) at any time without changing the PMR business logic.

### PMRResult Contract

```
PMRResult:
query_id: str
verdict: Literal["allow", "abstain"]
# "allow" → there are sufficiently relevant candidates
# "abstain" → no candidates pass the threshold — the system does not dare answer

candidates: list[RankedCandidate]
# RankedCandidate = HPVDCandidate + cross_encoder_score + final_rank

diagnostics: PMRDiagnostics
# reranking_latency_ms, cross_encoder_used, threshold_applied, dropped_count
```

---

## Scoring Strategy in PMR

### Strategy 1: Cross-Encoder Override (Cascade)

The RRF is used purely as a first-stage filter. The cross-encoder becomes the final score.

```
Step 1: HPVD → top 20 candidates via RRF
Step 2: Cross-encoder → score all 20 candidates
Step 3: Re-rank by cross_encoder_score
Step 4: Filter: drop if cross_encoder_score < threshold (e.g., 0.5)
```

- **Pro:** Most accurate. RRF does not affect the final ranking.
- **Con:** RRF may have dropped candidates that were actually relevant in the first stage.

### Strategy 2: Weighted Fusion

Combine RRF scores and cross-encoder scores with weights.

```
final_score = α × normalized_rrf_score + (1-α) × cross_encoder_score
# Default α = 0.3 (prefer a heavier cross-encoder)
```

- **Pro:** Utilizes both signals, more robust.
- **Con:** Requires α calibration for each domain.

### Strategy 3: Cross-Encoder as a Hard Gate

The cross-encoder is only used as a binary filter (relevant/irrelevant), not a reranker.

```
If cross_encoder_score < threshold → drop the candidate, no reordering required.
```

- **Pro:** Fastest. The cross-encoder only reduces the number of candidates.
- **Con:** Underutilizes the potential of the cross-encoder for precise reranking.

**Recommended: Strategy 1 (Cascade)** — cleanest and easiest to debug. If a fallback is needed when the cross-encoder is unavailable, PMR can be degraded to Strategy 3.

---

## Relationship of PMR to the HPVD Philosophy

It is important to emphasize the clear division of responsibilities:

| Responsibilities | HPVD | PMR |
|---|---|---|
| Candidate retrieval | ✅ | ❌ |
| BM25 sparse search | ✅ | ❌ |
| Vector dense search | ✅ | ❌ |
| RRF fusion | ✅ | ❌ |
| Compression-aware reranking | ❌ | ✅ (Cross-Encoder) |
| Relevance thresholding | ❌ | ✅ |
| Verdict (allow/abstain) | ❌ | ✅ |
| Business rule enforcement | ❌ | ❌ (located in Domain Service) |

HPVD should not know about Cross-Encoder. PMR should not know about BM25 or pgvector. They communicate only through `HPVDResult`.

---

## Open Questions (Decision Required Before Implementation)

1. **Hosting Model**: Which option should we choose for Cross-Encoder? Local (SentenceTransformer), Cohere API, or LLM-based? This impacts infrastructure requirements.

2. **Calibration Threshold**: What `cross_encoder_score` value is considered "relevant enough" for domain products in this governance platform? Labeled data or human evaluation is required to determine this.

3. **PMR Scope**: Is PMR only for the `products` domain, or will it be used cross-domain (policy, knowledge)? This determines where the `pmr/` module will be created.

4. **Fallback Behavior**: What happens if the cross-encoder is unavailable (model down, API timeout)? Does PMR fallback to the RRF result, or does the entire query fail?

5. **Latency Budget**: Cross-encoders across 20 candidates will increase latency. What is an acceptable latency budget for the `/products/search` endpoint?