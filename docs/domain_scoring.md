# Domain Scoring in PMR

## Overview

Domain scoring is the business-aware layer of the PMR pipeline. It evaluates each candidate against operational signals beyond semantic relevance: which department owns it, how trustworthy the source is, which tenant it belongs to, how complete the document is, and how confident the retrieval layer was.

Domain scoring is applied **identically** in both PMR V1 and V2. The only difference is which final formula consumes the scores.

---

## The Five Domain Scores

### 1. Department Score (`department_score`)

**Purpose**: Does the candidate belong to the right department for this query?

**Source field**: `candidate.department`

**Configuration** (`config/*_defaults.py`):

```python
"current_department": "finance",        # set per query context
"department_match": {
    "same": 1.0,            # candidate.department == current_department
    "related": 0.6,         # candidate.department is in related_pairs with current
    "unrelated": 0.0,       # no match
    "related_pairs": [
        ["operations", "logistics"],
        ["sales", "product"],
        ["hr", "operations"],
        ["finance", "operations"],
        ["support", "operations"],
    ],
}
```

**Scoring logic**:

```python
def compute_department_score(candidate, current_dept, dept_config):
    candidate_dept = candidate.department
    if not candidate_dept:
        return dept_config["unrelated"]          # 0.0
    if candidate_dept == current_dept:
        return dept_config["same"]               # 1.0
    for a, b in dept_config["related_pairs"]:
        if {a, b} == {candidate_dept, current_dept}:
            return dept_config["related"]        # 0.6
    return dept_config["unrelated"]              # 0.0
```

**Examples from mock data**:

| Query (current_dept) | Candidate | Department | Score |
|---|---|---|---|
| Q001 — reimbursement (finance) | DOC_001 (reimbursement policy) | finance | 1.0 |
| Q001 — reimbursement (finance) | DOC_004 (leave policy) | hr | 0.0 |
| Q010 — harassment (hr) | DOC_001 (harassment policy) | hr | 1.0 |
| Q010 — harassment (hr) | DOC_004 (IT security) | it | 0.0 |
| Q006 — Singapore shipping (logistics) | DOC_005 (domestic shipping) | logistics | 1.0 |
| Q003 — missing delivery (operations) | DOC_001 (missing package SOP) | operations | 1.0 |
| Q003 — missing delivery (operations) | DOC_002 (carrier claim) | logistics | 0.6 (related) |

---

### 2. Tenant Score (`tenant_score`)

**Purpose**: Does the candidate belong to the query's tenant or a closely related one?

**Source field**: `candidate.tenant_id`

**Configuration**:

```python
"current_tenant_id": "claims",
"tenant_priority": {
    "same": 1.0,       # candidate.tenant_id == current_tenant_id
    "global": 0.6,     # candidate.tenant_id == "global"
    "other": 0.0,      # any other tenant
}
```

**Examples**:

| Query (current_tenant) | Candidate | Tenant | Score |
|---|---|---|---|
| Q001 (claims) | DOC_001 (reimbursement policy) | claims | 1.0 |
| Q001 (claims) | DOC_004 (leave policy) | hr | 0.0 |
| Q004 (sales) | DOC_001 (return policy) | sales | 1.0 |
| Q004 (sales) | DOC_004 (chat about monitor) | support | 0.0 |
| Q010 (hr) | DOC_001 (harassment policy) | hr | 1.0 |
| Q010 (hr) | DOC_004 (IT security) | it | 0.0 |

---

### 3. Trust Score (`trust_score`)

**Purpose**: How authoritative is the source of this candidate?

**Source field**: `candidate.source_type`

**Configuration**:

```python
"source_trust": {
    "official_policy":   1.0,
    "sop_repository":    0.9,
    "product_catalog":   0.85,
    "knowledge_base":    0.8,
    "wiki":              0.6,
    "chat_transcript":   0.3,
    # any missing source_type defaults to 0.5
}
```

**Examples**:

| Candidate | Source Type | Score |
|---|---|---|
| Official reimbursement policy | official_policy | 1.0 |
| Missing package SOP | sop_repository | 0.9 |
| ProScan X120 datasheet | product_catalog | 0.85 |
| FAQ about toner cartridges | knowledge_base | 0.8 |
| Printer maintenance wiki | wiki | 0.6 |
| Agent transcript (missing order) | chat_transcript | 0.3 |

**Key impact**: In Q008 (bulk discounts), DOC_001 is a chat transcript (trust=0.3) with high RRF. DOC_002 is an official policy (trust=1.0) with slightly lower RRF. After domain scoring, DOC_002 overtakes DOC_001.

---

### 4. Completeness Score (`completeness_score`)

**Purpose**: How thorough is the candidate document?

**Source field**: `candidate.completeness_score` (pre-populated, 0.0–1.0)

No transformation is applied — this score is passed through as-is from the data layer.

**Examples**:

| Candidate Type | Typical Range |
|---|---|
| Official policies | 0.90–0.98 |
| SOPs and manuals | 0.88–0.94 |
| FAQ entries | 0.75–0.84 |
| Wiki articles | 0.55–0.88 |
| Chat transcripts | 0.25–0.42 |

---

### 5. Confidence Score (`confidence_score`)

**Purpose**: How confident is the HPVD retrieval layer that this candidate is relevant?

**Source fields**: `candidate.rrf_score`, `candidate.bm25_score`, `candidate.vector_score`, `candidate.semantic_score` (V2 only)

**Configuration** (V1):

```python
"confidence_weights": {
    "rrf":    0.40,
    "bm25":   0.30,
    "vector": 0.30,
}
```

**Configuration** (V2 — includes semantic):

```python
"confidence_weights": {
    "rrf":      0.25,
    "bm25":     0.20,
    "vector":   0.25,
    "semantic": 0.30,
}
```

**Formula**:

```python
# V1
raw = 0.40 * rrf + 0.30 * norm(bm25) + 0.30 * vector

# V2
raw = 0.25 * rrf + 0.20 * norm(bm25) + 0.25 * vector + 0.30 * semantic
```

where `norm(bm25) = min(bm25 / 20.0, 1.0)`

**Examples**:

| Query | Candidate | rrf | bm25 | vector | V1 Confidence |
|---|---|---|---|---|---|
| Q002 — toner | DOC_001 (compatibility guide) | 0.053 | 18.34 | 0.94 | ~0.85 |
| Q002 — toner | DOC_005 (forum discussion) | 0.019 | 6.78 | 0.59 | ~0.34 |
| Q009 — cafeteria (irrelevant) | DOC_001 (leave policy) | 0.018 | 5.12 | 0.35 | ~0.22 |

---

## Weight Distribution

Both V1 and V2 combine the five domain scores with the semantic score into one weighted final score:

### V1 — Final Score

```python
final_score = (
    0.40 * semantic_score +
    0.20 * department_score +
    0.15 * tenant_score +
    0.10 * trust_score +
    0.05 * completeness_score +
    0.10 * confidence_score
)
```

### V2 — Answer Probability

```python
answer_probability = (
    0.35 * semantic_score +
    0.20 * department_score +
    0.15 * tenant_score +
    0.10 * trust_score +
    0.05 * completeness_score +
    0.15 * confidence_score
)
```

### Comparison

| Component | V1 Weight | V2 Weight |
|---|---|---|
| Semantic | 0.40 | 0.35 |
| Department | 0.20 | 0.20 |
| Tenant | 0.15 | 0.15 |
| Trust | 0.10 | 0.10 |
| Completeness | 0.05 | 0.05 |
| Confidence | 0.10 | 0.15 |

V2 shifts 0.05 from semantic to confidence because V2's confidence score already incorporates the semantic signal internally, so the outer weight is adjusted to avoid double-counting.

---

## Walkthrough: Q008 — Bulk Discounts

This query tests the case where a chat transcript (DOC_001) outranks an official policy (DOC_002) in pure retrieval, but the ranker should correct this.

| Signal | DOC_001 (chat) | DOC_002 (policy) |
|---|---|---|
| semantic_score | 0.9 (dummy) | 0.8 (dummy) |
| **department_score** — both are sales/dept=sales, current_dept=sales | **1.0** | **1.0** |
| **tenant_score** — both are sales tenant | **1.0** | **1.0** |
| **trust_score** — chat vs official_policy | **0.3** | **1.0** |
| **completeness_score** — fragmentary vs comprehensive | **0.30** | **0.97** |
| **confidence_score** — similar retrieval strength | ~0.78 | ~0.77 |

**V1 Final Score**:

| | DOC_001 | DOC_002 |
|---|---|---|
| semantic | 0.40 × 0.9 = 0.360 | 0.40 × 0.8 = 0.320 |
| department | 0.20 × 1.0 = 0.200 | 0.20 × 1.0 = 0.200 |
| tenant | 0.15 × 1.0 = 0.150 | 0.15 × 1.0 = 0.150 |
| trust | 0.10 × 0.3 = 0.030 | 0.10 × 1.0 = 0.100 |
| completeness | 0.05 × 0.30 = 0.015 | 0.05 × 0.97 = 0.049 |
| confidence | 0.10 × 0.78 = 0.078 | 0.10 × 0.77 = 0.077 |
| **Total** | **0.833** | **0.896** ✅ |

DOC_002 (official policy) correctly overtakes DOC_001 (chat transcript) by 0.063 points, driven by trust and completeness. The ranker corrects the retrieval order.

---

## Summary Table

| Score | Meaning | Data Source | Key Config | Range |
|---|---|---|---|---|
| `department_score` | Department relevance | `candidate.department` | `department_match` | 0.0, 0.6, 1.0 |
| `tenant_score` | Tenant affiliation | `candidate.tenant_id` | `tenant_priority` | 0.0, 0.6, 1.0 |
| `trust_score` | Source authority | `candidate.source_type` | `source_trust` | 0.3–1.0 |
| `completeness_score` | Document thoroughness | `candidate.completeness_score` | (passed through) | 0.0–1.0 |
| `confidence_score` | Retrieval signal strength | `rrf`, `bm25`, `vector`, `semantic` | `confidence_weights` | 0.0–1.0 |
