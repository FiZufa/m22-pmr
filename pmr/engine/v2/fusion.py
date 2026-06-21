from __future__ import annotations

from pmr.core.models import ScoredCandidate


def compute_answer_probability(
    candidate: ScoredCandidate,
    weights: dict[str, float],
) -> float:
    return (
        weights["semantic"] * candidate.semantic_score
        + weights["business"] * candidate.business_score
        + weights["tenant"] * candidate.tenant_score
        + weights["trust"] * candidate.trust_score
        + weights["completeness"] * candidate.completeness_score
        + weights["confidence"] * candidate.confidence_score
    )


def run_probability_fusion(
    candidates: list[ScoredCandidate],
    config: dict,
) -> list[ScoredCandidate]:
    weights = config["weights"]
    for c in candidates:
        c.answer_probability = compute_answer_probability(c, weights)
    candidates.sort(key=lambda c: c.answer_probability, reverse=True)
    return candidates
