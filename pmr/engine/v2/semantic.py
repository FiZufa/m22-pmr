from __future__ import annotations

from pmr.core.interfaces import CrossEncoderPort
from pmr.core.models import HPVDResult, ScoredCandidate


def run_semantic_assessment(
    hpvd_result: HPVDResult,
    cross_encoder: CrossEncoderPort,
) -> list[ScoredCandidate]:
    texts = [c.candidate_text for c in hpvd_result.candidates]
    scores = cross_encoder.rerank(hpvd_result.query, texts)
    scored: list[ScoredCandidate] = []
    for candidate, score in zip(hpvd_result.candidates, scores):
        scored.append(ScoredCandidate(
            **candidate.model_dump(),
            semantic_score=score,
        ))
    return scored
