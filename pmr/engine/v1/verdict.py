from __future__ import annotations

from pmr.core.models import ScoredCandidate, PMRResult, PMRDiagnostics, Verdict


def compute_final_score(
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


def run_verdict_engine(
    candidates: list[ScoredCandidate],
    hpvd_result,
    config: dict,
    dropped_before: int,
    cross_encoder_name: str = "",
) -> PMRResult:
    weights = config["weights"]
    final_threshold = config["final_threshold"]

    for c in candidates:
        c.final_score = compute_final_score(c, weights)
        c.verdict = "ALLOW" if c.final_score >= final_threshold else "ABSTAIN"

    candidates.sort(key=lambda c: c.final_score, reverse=True)

    passed = [c for c in candidates if c.verdict == "ALLOW"]
    overall: Verdict = "ALLOW" if passed else "ABSTAIN"

    reason_codes = _build_reason_codes(passed)

    diagnostics = PMRDiagnostics(
        total_candidates=len(candidates) + dropped_before,
        dropped_count=dropped_before,
        cross_encoder_used=cross_encoder_name,
        reason_codes=reason_codes,
    )

    return PMRResult(
        query_id=hpvd_result.query_id,
        pipeline_version="v1",
        candidates=candidates,
        verdict=overall,
        diagnostics=diagnostics,
    )


def _build_reason_codes(allowed: list[ScoredCandidate]) -> list[str]:
    codes: list[str] = []
    if allowed:
        codes.append("HAS_ALLOWED_CANDIDATES")
        top = allowed[0]
        if top.semantic_score >= 0.8:
            codes.append("HIGH_SEMANTIC_MATCH")
        if top.tenant_score >= 0.8:
            codes.append("TENANT_MATCH")
        if top.trust_score >= 0.8:
            codes.append("TRUSTED_SOURCE")
    else:
        codes.append("NO_ALLOWED_CANDIDATES")
    return codes
