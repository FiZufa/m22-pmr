from __future__ import annotations

from dataclasses import dataclass

from pmr.core.models import HPVDResult


@dataclass
class FeatureSet:
    rrf_score: float
    bm25_score: float
    vector_score: float
    metadata_score: float


def extract_evidence(hpvd_result: HPVDResult) -> list[FeatureSet]:
    return [
        FeatureSet(
            rrf_score=c.rrf_score,
            bm25_score=c.bm25_score,
            vector_score=c.vector_score,
            metadata_score=c.metadata_score,
        )
        for c in hpvd_result.candidates
    ]
