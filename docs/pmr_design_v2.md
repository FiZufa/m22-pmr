# PMR (Probability Multimodal Reasoning) Layer Design

## Overview

PMR (Probability Multimodal Reasoning) is a post-retrieval reasoning and ranking layer designed to estimate the probability that a retrieved candidate can correctly answer a user query.

PMR operates after retrieval fusion (RRF) and before response generation.

The primary objective is not only to rank candidates, but also to determine whether a candidate is sufficiently relevant, trustworthy, and appropriate for downstream answer generation.

The output of PMR is:

* Answer Probability
* Verdict (ALLOW / ABSTAIN)
* Ranking Diagnostics

---

# Position in Overall Architecture

```text
Query
    ↓

Service Layer
    ↓

HPVD Kernel Search

    ├─ Query Understanding
    │   ├─ Intent Detection
    │   ├─ Search Model Selection
    │   └─ Filter Extraction
    │
    └─ Retriever Selector
        ├─ Sparse BM25
        ├─ Vector Retrieval
        ├─ Metadata Filter
        ├─ Candidate Gate
        └─ Tenant Custom Retriever

    ↓

Candidate Normalization
    ↓

RRF Fusion
    ↓

HPVDResult
    ↓

PMR Layer
    ↓

PMRResult
    ↓

Product Service
    ↓

Consumer Response
```

---

# PMR Responsibilities

The PMR layer is responsible for:

* Semantic relevance assessment
* Semantic quality filtering
* Business rule evaluation
* Tenant-aware ranking
* Source trust evaluation
* Document completeness evaluation
* Confidence estimation
* Probability calculation
* Allow / Abstain decision making
* Ranking diagnostics generation

PMR remains independent from retrieval implementation.

---

# PMR High-Level Workflow

```text
HPVDResult
    ↓

Evidence Extraction
    ↓

Semantic Assessment
(Cross Encoder)
    ↓

Semantic Gate
    ↓

Domain Scoring
 ├─ Business Assessment
 ├─ Tenant Assessment
 ├─ Trust Assessment
 └─ Completeness Assessment

    ↓

Confidence Assessment
    ↓

Probability Fusion
    ↓

Verdict Engine
    ↓

PMRResult
```

---

# Input Contract

## HPVDResult

PMR consumes retrieval candidates generated from the HPVD retrieval layer.

Example:

```json
{
  "candidate_id": "DOC_001",
  "candidate_text": "Claim reimbursement SOP",

  "bm25_score": 12.5,
  "vector_score": 0.87,
  "metadata_score": 0.90,

  "bm25_rank": 2,
  "vector_rank": 1,

  "rrf_score": 0.034,

  "source_type": "official_policy",
  "tenant_id": "claims",

  "metadata": {}
}
```

---

# Stage 1: Evidence Extraction

## Objective

Extract retrieval signals and metadata required for PMR processing.

## Input Signals

* BM25 score
* Vector score
* Metadata score
* RRF score
* Candidate metadata

## Output

```python
FeatureSet(
    retrieval_features,
    metadata_features
)
```

Example:

```python
{
    "rrf_score": 0.034,
    "bm25_score": 12.5,
    "vector_score": 0.87
}
```

---

# Stage 2: Semantic Assessment

## Objective

Measure semantic relevance between query and candidate text.

## Method

Cross-Encoder Reranker

Example:

```python
semantic_score = cross_encoder(
    query,
    candidate_text
)
```

## Output

```python
semantic_score
```

Range:

```text
0.0 - 1.0
```

Interpretation:

> Probability-like relevance signal indicating how well the candidate matches the query.

---

# Stage 3: Semantic Gate

## Objective

Remove semantically irrelevant candidates before domain scoring.

## Rationale

Business or tenant rules should never rescue an irrelevant document.

## Example Rule

```python
if semantic_score < semantic_threshold:
    verdict = "ABSTAIN"
```

Example threshold:

```python
semantic_threshold = 0.45
```

## Result

Candidates failing the semantic gate are removed from further processing.

---

# Stage 4: Domain Scoring

## Objective

Evaluate domain-specific suitability of the candidate.

Domain scoring consists of multiple independent signals.

---

## 4.1 Business Assessment

### Purpose

Measure business relevance.

### Examples

* Department match
* Policy type match
* Product match
* Freshness score
* Regulatory relevance

### Output

```python
business_score
```

Range:

```text
0.0 - 1.0
```

---

## 4.2 Tenant Assessment

### Purpose

Prioritize tenant-owned knowledge.

### Example

| Scenario         | Score |
| ---------------- | ----- |
| Same Tenant      | 1.0   |
| Global Knowledge | 0.6   |
| Other Tenant     | 0.0   |

### Output

```python
tenant_score
```

---

## 4.3 Trust Assessment

### Purpose

Measure trustworthiness of the information source.

### Example Trust Registry

| Source Type     | Trust Score |
| --------------- | ----------- |
| Official Policy | 1.00        |
| SOP Repository  | 0.90        |
| Knowledge Base  | 0.80        |
| Wiki            | 0.60        |
| Chat Transcript | 0.30        |

### Output

```python
trust_score
```

---

## 4.4 Completeness Assessment

### Purpose

Measure document completeness.

### Example

```python
completeness_score =
available_sections /
required_sections
```

### Output

```python
completeness_score
```

Range:

```text
0.0 - 1.0
```

---

# Stage 5: Confidence Assessment

## Objective

Estimate confidence using retrieval and ranking evidence.

Unlike domain scoring, confidence is derived from retrieval and semantic signals.

## Input Signals

* RRF score
* BM25 score
* Vector score
* Semantic score

Example:

```python
confidence_score =
f(
    rrf_score,
    bm25_score,
    vector_score,
    semantic_score
)
```

## Output

```python
confidence_score
```

Range:

```text
0.0 - 1.0
```

Interpretation:

> Estimated confidence that retrieval and ranking evidence support the candidate.

---

# Stage 6: Probability Fusion

## Objective

Combine semantic, domain, and confidence signals into a single answer probability.

## Inputs

* Semantic Score
* Business Score
* Tenant Score
* Trust Score
* Completeness Score
* Confidence Score

## Example Formula

```python
answer_probability =
0.35 * semantic_score +
0.20 * business_score +
0.15 * tenant_score +
0.10 * trust_score +
0.05 * completeness_score +
0.15 * confidence_score
```

## Output

```python
answer_probability
```

Range:

```text
0.0 - 1.0
```

Interpretation:

> Estimated probability that the candidate can correctly answer the user query.

---

# Stage 7: Verdict Engine

## Objective

Determine whether the candidate is eligible for downstream answer generation.

## Rule 1: Semantic Gate

```python
if semantic_score < semantic_threshold:
    verdict = "ABSTAIN"
```

## Rule 2: Probability Threshold

```python
if answer_probability >= probability_threshold:
    verdict = "ALLOW"
else:
    verdict = "ABSTAIN"
```

Example:

```python
semantic_threshold = 0.45
probability_threshold = 0.75
```

---

# Output Contract

## PMRResult

```json
{
  "candidate_id": "DOC_001",

  "answer_probability": 0.89,

  "verdict": "ALLOW",

  "semantic_score": 0.91,

  "business_score": 0.82,

  "tenant_score": 1.00,

  "trust_score": 0.95,

  "completeness_score": 0.90,

  "confidence_score": 0.88,

  "diagnostics": {
    "rrf_rank": 2,
    "cross_encoder_rank": 1,
    "reason_codes": [
      "HIGH_SEMANTIC_MATCH",
      "TENANT_MATCH",
      "TRUSTED_SOURCE"
    ]
  }
}
```

---

# Design Principles

1. Retrieval Agnostic
2. Explainable by Design
3. Tenant Extensible
4. Safe by Default
5. Probability Driven
6. Future Learning-to-Rank Ready
7. Semantic Relevance First
8. Domain Rules Cannot Rescue Irrelevant Documents

```
