from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


Verdict = Literal["ALLOW", "ABSTAIN"]


class HPVDCandidate(BaseModel):
    candidate_id: str
    candidate_text: str

    bm25_score: float
    vector_score: float
    metadata_score: float
    bm25_rank: int | None = None
    vector_rank: int | None = None
    metadata_rank: int | None = None

    rrf_score: float

    source_type: str
    tenant_id: str
    department: str | None = None
    document_type: str | None = None
    completeness_score: float = 0.0

    created_at: str | None = None
    last_updated: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class HPVDResult(BaseModel):
    query_id: str
    query: str
    candidates: list[HPVDCandidate]


class ScoredCandidate(HPVDCandidate):
    semantic_score: float = 0.0
    business_score: float = 0.0
    tenant_score: float = 0.0
    trust_score: float = 0.0
    confidence_score: float = 0.0
    final_score: float = 0.0
    answer_probability: float = 0.0
    verdict: Verdict = "ABSTAIN"


class PMRDiagnostics(BaseModel):
    total_candidates: int = 0
    dropped_count: int = 0
    gated_count: int = 0
    reranking_latency_ms: float = 0.0
    cross_encoder_used: str = ""
    reason_codes: list[str] = Field(default_factory=list)


class PMRResult(BaseModel):
    query_id: str
    pipeline_version: str
    candidates: list[ScoredCandidate]
    verdict: Verdict = "ABSTAIN"
    diagnostics: PMRDiagnostics = Field(default_factory=PMRDiagnostics)
