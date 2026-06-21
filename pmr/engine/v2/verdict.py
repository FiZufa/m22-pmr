from __future__ import annotations

from pmr.core.models import ScoredCandidate, PMRResult, PMRDiagnostics, Verdict


def run_verdict_engine(
    gated_count: int,
    passed: list[ScoredCandidate],
    gated: list[ScoredCandidate],
    hpvd_result,
    config: dict,
    cross_encoder_name: str = "",
) -> PMRResult:
    probability_threshold = config["probability_threshold"]

    for c in passed:
        c.verdict = "ALLOW" if c.answer_probability >= probability_threshold else "ABSTAIN"

    allowed = [c for c in passed if c.verdict == "ALLOW"]
    overall: Verdict = "ALLOW" if allowed else "ABSTAIN"

    reason_codes = _build_reason_codes(allowed, gated)

    diagnostics = PMRDiagnostics(
        total_candidates=len(passed) + len(gated),
        dropped_count=0,
        gated_count=gated_count,
        cross_encoder_used=cross_encoder_name,
        reason_codes=reason_codes,
    )

    all_candidates = passed + gated

    return PMRResult(
        query_id=hpvd_result.query_id,
        pipeline_version="v2",
        candidates=all_candidates,
        verdict=overall,
        diagnostics=diagnostics,
    )


def _build_reason_codes(allowed: list[ScoredCandidate], gated: list[ScoredCandidate]) -> list[str]:
    codes: list[str] = []
    if gated:
        codes.append("SEMANTIC_GATE_REMOVED")
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
