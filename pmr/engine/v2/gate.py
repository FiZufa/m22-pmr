from __future__ import annotations

from pmr.core.models import ScoredCandidate


class SemanticGateResult:
    def __init__(
        self,
        passed: list[ScoredCandidate],
        gated: list[ScoredCandidate],
    ):
        self.passed = passed
        self.gated = gated


def apply_semantic_gate(
    candidates: list[ScoredCandidate],
    threshold: float,
) -> SemanticGateResult:
    passed: list[ScoredCandidate] = []
    gated: list[ScoredCandidate] = []
    for c in candidates:
        if c.semantic_score >= threshold:
            passed.append(c)
        else:
            gated.append(c)
    return SemanticGateResult(passed=passed, gated=gated)
