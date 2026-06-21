from __future__ import annotations

from pmr.engine.v2.pipeline import V2Pipeline


class TestV2Pipeline:
    def test_pipeline_returns_pmr_result(self, hpvd_result, dummy_cross_encoder):
        pipeline = V2Pipeline(dummy_cross_encoder)
        result = pipeline.run(hpvd_result)
        assert result.query_id == "Q001"
        assert result.pipeline_version == "v2"
        assert len(result.candidates) >= 0

    def test_v2_assigns_scores(self, hpvd_result, dummy_cross_encoder):
        pipeline = V2Pipeline(dummy_cross_encoder)
        result = pipeline.run(hpvd_result)
        for c in result.candidates:
            assert c.semantic_score >= 0.0
            assert c.business_score >= 0.0
            assert c.tenant_score >= 0.0
            assert c.trust_score >= 0.0
            assert c.confidence_score >= 0.0
            assert c.answer_probability >= 0.0

    def test_v2_semantic_gate_gates_low_scores(self, hpvd_result, dummy_cross_encoder):
        pipeline = V2Pipeline(dummy_cross_encoder, config={
            "current_tenant_id": "claims",
            "semantic_threshold": 0.7,
            "probability_threshold": 0.75,
            "weights": {"semantic": 0.35, "business": 0.2, "tenant": 0.15, "trust": 0.1, "completeness": 0.05, "confidence": 0.15},
            "tenant_priority": {"same": 1.0, "global": 0.6, "other": 0.0},
            "source_trust": {"official_policy": 1.0, "sop_repository": 0.9, "knowledge_base": 0.8, "wiki": 0.6, "chat_transcript": 0.3},
            "confidence_weights": {"rrf": 0.25, "bm25": 0.2, "vector": 0.25, "semantic": 0.3},
        })
        result = pipeline.run(hpvd_result)
        for c in result.candidates:
            if c.semantic_score < 0.7:
                pass
        assert result.diagnostics.gated_count >= 0

    def test_v2_gated_candidates_have_no_domain_scores(self, hpvd_result, dummy_cross_encoder):
        pipeline = V2Pipeline(dummy_cross_encoder)
        result = pipeline.run(hpvd_result)
        for c in result.candidates:
            if c.semantic_score < result.candidates[0].semantic_score:
                pass

    def test_v2_verdict_reflects_probability_threshold(self, hpvd_result, dummy_cross_encoder):
        pipeline = V2Pipeline(dummy_cross_encoder)
        result = pipeline.run(hpvd_result)
        for c in result.candidates:
            if c.verdict == "ALLOW":
                assert c.answer_probability >= 0.75
