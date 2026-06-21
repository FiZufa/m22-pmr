from __future__ import annotations

import json
from pathlib import Path

import pytest

from pmr.core.models import HPVDResult
from pmr.adapters.cross_encoder import DummyCrossEncoder


@pytest.fixture
def mock_data_path() -> Path:
    return Path(__file__).parent.parent / "data" / "mock_data_1.json"


@pytest.fixture
def hpvd_result(mock_data_path) -> HPVDResult:
    with open(mock_data_path, encoding="utf-8") as f:
        data = json.load(f)
    return HPVDResult(**data)


@pytest.fixture
def dummy_cross_encoder() -> DummyCrossEncoder:
    return DummyCrossEncoder()
