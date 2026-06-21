from __future__ import annotations

import json
from pathlib import Path

from pmr.core.models import HPVDResult, PMRResult, ScoredCandidate


class TestHPVDResult:
    def test_load_from_mock_data(self, mock_data_path: Path):
        with open(mock_data_path, encoding="utf-8") as f:
            data = json.load(f)
        result = HPVDResult(**data)
        assert result.query_id == "Q001"
        assert result.query == "How do I submit a reimbursement claim?"
        assert len(result.candidates) == 5
        assert result.candidates[0].candidate_id == "DOC_001"

    def test_candidate_has_expected_fields(self, hpvd_result: HPVDResult):
        c = hpvd_result.candidates[0]
        assert c.bm25_score == 15.42
        assert c.vector_score == 0.91
        assert c.rrf_score == 0.048
        assert c.source_type == "official_policy"
        assert c.tenant_id == "claims"


class TestScoredCandidate:
    def test_defaults(self):
        c = ScoredCandidate(
            candidate_id="X",
            candidate_text="text",
            bm25_score=0.0,
            vector_score=0.0,
            metadata_score=0.0,
            rrf_score=0.0,
            source_type="wiki",
            tenant_id="global",
        )
        assert c.semantic_score == 0.0
        assert c.final_score == 0.0
        assert c.answer_probability == 0.0
        assert c.verdict == "ABSTAIN"


class TestPMRResult:
    def test_default_diagnostics(self):
        result = PMRResult(
            query_id="Q001",
            pipeline_version="v1",
            candidates=[],
        )
        assert result.verdict == "ABSTAIN"
        assert result.diagnostics.total_candidates == 0
