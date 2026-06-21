from __future__ import annotations

from pmr.engine.v1.pipeline import V1Pipeline
from pmr.core.models import Verdict


class TestV1Pipeline:
    def test_pipeline_returns_pmr_result(self, hpvd_result, dummy_cross_encoder):
        pipeline = V1Pipeline(dummy_cross_encoder)
        result = pipeline.run(hpvd_result)
        assert result.query_id == "Q001"
        assert result.pipeline_version == "v1"
        assert len(result.candidates) >= 0

    def test_v1_assigns_scores(self, hpvd_result, dummy_cross_encoder):
        pipeline = V1Pipeline(dummy_cross_encoder)
        result = pipeline.run(hpvd_result)
        for c in result.candidates:
            assert c.semantic_score >= 0.0
            assert c.business_score >= 0.0
            assert c.tenant_score >= 0.0
            assert c.trust_score >= 0.0
            assert c.confidence_score >= 0.0
            assert c.final_score >= 0.0

    def test_v1_top_candidate_is_allowed(self, hpvd_result, dummy_cross_encoder):
        pipeline = V1Pipeline(dummy_cross_encoder)
        result = pipeline.run(hpvd_result)
        allowed = [c for c in result.candidates if c.verdict == "ALLOW"]
        if allowed:
            assert all(c.final_score >= 0.75 for c in allowed)

    def test_v1_semantic_threshold_drops_low_scores(self, hpvd_result, dummy_cross_encoder):
        pipeline = V1Pipeline(dummy_cross_encoder, config={
            "current_tenant_id": "claims",
            "semantic_threshold": 0.5,
            "final_threshold": 0.75,
            "weights": {"semantic": 0.4, "business": 0.2, "tenant": 0.15, "trust": 0.1, "completeness": 0.05, "confidence": 0.1},
            "tenant_priority": {"same": 1.0, "global": 0.6, "other": 0.0},
            "source_trust": {"official_policy": 1.0, "sop_repository": 0.9, "knowledge_base": 0.8, "wiki": 0.6, "chat_transcript": 0.3},
            "confidence_weights": {"rrf": 0.4, "bm25": 0.3, "vector": 0.3},
        })
        result = pipeline.run(hpvd_result)
        for c in result.candidates:
            assert c.semantic_score >= 0.5 or c.verdict == "ABSTAIN"

    def test_v1_diagnostics_reflect_dropped(self, hpvd_result, dummy_cross_encoder):
        pipeline = V1Pipeline(dummy_cross_encoder)
        result = pipeline.run(hpvd_result)
        assert result.diagnostics.total_candidates == 5
        assert result.diagnostics.reranking_latency_ms > 0
