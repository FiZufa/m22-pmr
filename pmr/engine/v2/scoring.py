from __future__ import annotations

from pmr.core.models import ScoredCandidate, HPVDResult


def compute_department_score(
    candidate: ScoredCandidate,
    current_dept: str,
    dept_config: dict,
) -> float:
    candidate_dept = candidate.department
    if not candidate_dept:
        return dept_config["unrelated"]
    if candidate_dept == current_dept:
        return dept_config["same"]
    for a, b in dept_config["related_pairs"]:
        if {a, b} == {candidate_dept, current_dept}:
            return dept_config["related"]
    return dept_config["unrelated"]


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
    current_dept = config.get("current_department", "operations")
    for c in candidates:
        c.department_score = compute_department_score(c, current_dept, config["department_match"])
        c.tenant_score = compute_tenant_score(c, tenant_id, config["tenant_priority"])
        c.trust_score = compute_trust_score(c, config["source_trust"])
    return candidates
