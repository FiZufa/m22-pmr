# PMR (Probability Multimodal Reasoning) Layer Design - V1

## Overview

PMR (Probability Multimodal Reasoning) is a post-retrieval ranking and reasoning layer designed to evaluate retrieval candidates and estimate their suitability for downstream answer generation.

PMR operates after retrieval fusion (RRF) and before response generation.

The objective of PMR V1 is to:

* Improve ranking quality beyond RRF
* Apply semantic relevance scoring
* Apply domain-specific ranking rules
* Produce a final candidate score
* Determine whether a candidate should be returned

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

* Semantic reranking
* Business rule scoring
* Tenant-aware scoring
* Source trust scoring
* Completeness scoring
* Confidence scoring
* Final score calculation
* Candidate ranking
* Verdict generation

---

# PMR High-Level Workflow

```text
HPVDResult
    ↓

Semantic Assessment
(Cross Encoder)
    ↓

Threshold Filter
    ↓

Domain Scoring
 ├─ Business Score
 ├─ Tenant Priority
 ├─ Source Trust
 ├─ Completeness
 └─ Confidence

    ↓

Final Score Combiner
    ↓

Final Ranking
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

  "rrf_score": 0.034,

  "source_type": "official_policy",
  "tenant_id": "claims",

  "metadata": {}
}
```

---

# Stage 1: Semantic Assessment

## Objective

Measure semantic relevance between the user query and candidate text.

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

Example:

```python
0.91
```

Interpretation:

> Degree of semantic relevance between query and candidate.

---

# Stage 2: Threshold Filter

## Objective

Remove candidates with insufficient semantic relevance.

## Rule

```python
if semantic_score < threshold:
    verdict = "ABSTAIN"
```

Example:

```python
threshold = 0.45
```

Candidates passing the threshold continue to domain scoring.

---

# Stage 3: Domain Scoring

## Objective

Apply business and operational ranking signals.

---

## 3.1 Business Score

### Purpose

Measure business relevance.

### Examples

* Department match
* Product match
* Policy type match
* Freshness score

### Output

```python
business_score
```

Range:

```text
0.0 - 1.0
```

---

## 3.2 Tenant Priority

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

## 3.3 Source Trust

### Purpose

Promote trusted information sources.

### Example

| Source Type     | Score |
| --------------- | ----- |
| Official Policy | 1.00  |
| SOP Repository  | 0.90  |
| Knowledge Base  | 0.80  |
| Wiki            | 0.60  |
| Chat Transcript | 0.30  |

### Output

```python
trust_score
```

---

## 3.4 Completeness

### Purpose

Reward more complete documents.

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

---

## 3.5 Confidence

### Purpose

Represent retrieval confidence.

### Inputs

* RRF score
* BM25 score
* Vector score

### Example

```python
confidence_score =
f(
    rrf_score,
    bm25_score,
    vector_score
)
```

### Output

```python
confidence_score
```

---

# Stage 4: Final Score Combiner

## Objective

Combine semantic and domain signals into a final ranking score.

## Inputs

* Semantic Score
* Business Score
* Tenant Score
* Trust Score
* Completeness Score
* Confidence Score

## Example Formula

```python
final_score =
0.40 * semantic_score +
0.20 * business_score +
0.15 * tenant_score +
0.10 * trust_score +
0.05 * completeness_score +
0.10 * confidence_score
```

## Output

```python
final_score
```

Range:

```text
0.0 - 1.0
```

---

# Stage 5: Final Ranking

## Objective

Sort candidates by final score.

Example:

| Rank | Candidate | Final Score |
| ---- | --------- | ----------- |
| 1    | DOC_001   | 0.91        |
| 2    | DOC_003   | 0.87        |
| 3    | DOC_002   | 0.82        |

---

# Stage 6: Verdict Engine

## Objective

Determine whether the candidate should be returned.

## Rule

```python
if final_score >= final_threshold:
    verdict = "ALLOW"
else:
    verdict = "ABSTAIN"
```

Example:

```python
final_threshold = 0.75
```

---

# Output Contract

## PMRResult

```json
{
  "candidate_id": "DOC_001",

  "verdict": "ALLOW",

  "semantic_score": 0.91,

  "business_score": 0.82,

  "tenant_score": 1.00,

  "trust_score": 0.95,

  "completeness_score": 0.90,

  "confidence_score": 0.88,

  "final_score": 0.89,

  "diagnostics": {
    "rrf_rank": 2,
    "reason_codes": [
      "HIGH_SEMANTIC_MATCH",
      "TENANT_MATCH",
      "TRUSTED_SOURCE"
    ]
  }
}
```

---

# PMR V1 Design Principles

1. Simple and explainable
2. Retrieval-agnostic
3. Domain-aware ranking
4. Single-score ranking strategy
5. Suitable for rapid experimentation
6. Easy to extend with additional scoring signals
7. Baseline architecture for PMR evolution
