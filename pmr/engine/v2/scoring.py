from __future__ import annotations

from pmr.core.models import ScoredCandidate, HPVDResult


def compute_business_score(candidate: ScoredCandidate, hpvd_result: HPVDResult) -> float:
    return 1.0


def compute_tenant_score(
    candidate: ScoredCandidate,
    tenant_id: str,
    tenant_config: dict,
) -> float:
    if candidate.tenant_id == tenant_id:
        return tenant_config["same"]
    if candidate.tenant_id == "global":
        return tenant_config["global"]
    return tenant_config["other"]


def compute_trust_score(
    candidate: ScoredCandidate,
    trust_table: dict[str, float],
) -> float:
    return trust_table.get(candidate.source_type, 0.5)


def apply_domain_scoring(
    candidates: list[ScoredCandidate],
    hpvd_result: HPVDResult,
    config: dict,
) -> list[ScoredCandidate]:
    tenant_id = config.get("current_tenant_id", "global")
    for c in candidates:
        c.business_score = compute_business_score(c, hpvd_result)
        c.tenant_score = compute_tenant_score(c, tenant_id, config["tenant_priority"])
        c.trust_score = compute_trust_score(c, config["source_trust"])
    return candidates
