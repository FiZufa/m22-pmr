from __future__ import annotations

import json
from pathlib import Path

from pmr.core.models import HPVDResult


class TestAllMockData:
    def test_all_mock_files_load(self):
        data_dir = Path(__file__).parent.parent / "data"
        files = sorted(data_dir.glob("mock_data_Q*.json"))
        assert len(files) > 0, "No mock data files found"

        for f in files:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            result = HPVDResult(**data)
            assert result.query_id is not None
            assert len(result.candidates) >= 1

    def test_q002_product_compatibility(self):
        data = json.load(open(
            Path(__file__).parent.parent / "data" / "mock_data_Q002.json",
            encoding="utf-8",
        ))
        result = HPVDResult(**data)
        assert result.query_id == "Q002"
        assert len(result.candidates) == 5

    def test_q009_all_low_relevance(self):
        data = json.load(open(
            Path(__file__).parent.parent / "data" / "mock_data_Q009.json",
            encoding="utf-8",
        ))
        result = HPVDResult(**data)
        assert result.query_id == "Q009"
        for c in result.candidates:
            assert c.vector_score < 0.5

    def test_q010_hr_harassment(self):
        data = json.load(open(
            Path(__file__).parent.parent / "data" / "mock_data_Q010.json",
            encoding="utf-8",
        ))
        result = HPVDResult(**data)
        assert result.query_id == "Q010"
        assert len(result.candidates) == 5
