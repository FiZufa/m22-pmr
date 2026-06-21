from __future__ import annotations

from pmr.core.models import ScoredCandidate


def _normalize_bm25(raw: float, max_bm25: float = 20.0) -> float:
    return min(raw / max_bm25, 1.0)


def compute_confidence_score(
    candidate: ScoredCandidate,
    confidence_weights: dict[str, float],
) -> float:
    raw = (
        confidence_weights["rrf"] * candidate.rrf_score
        + confidence_weights["bm25"] * _normalize_bm25(candidate.bm25_score)
        + confidence_weights["vector"] * candidate.vector_score
        + confidence_weights["semantic"] * candidate.semantic_score
    )
    return min(max(raw, 0.0), 1.0)


def apply_confidence_assessment(
    candidates: list[ScoredCandidate],
    config: dict,
) -> list[ScoredCandidate]:
    for c in candidates:
        c.confidence_score = compute_confidence_score(c, config["confidence_weights"])
    return candidates
