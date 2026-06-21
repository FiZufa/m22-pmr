from __future__ import annotations

from pmr.core.models import ScoredCandidate


def filter_by_threshold(
    candidates: list[ScoredCandidate],
    semantic_threshold: float,
) -> list[ScoredCandidate]:
    return [c for c in candidates if c.semantic_score >= semantic_threshold]
