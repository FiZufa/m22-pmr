from __future__ import annotations

import json
from pathlib import Path

from pmr.core.models import HPVDResult
from pmr.engine.v1.pipeline import V1Pipeline
from pmr.engine.v2.pipeline import V2Pipeline
from pmr.adapters.cross_encoder import DummyCrossEncoder


def load_hpvd_result(path: str) -> HPVDResult:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return HPVDResult(**data)


def print_comparison(v1_result, v2_result):
    print(f"\n{'='*70}")
    print(f"Query [{v1_result.query_id}]: Comparison V1 vs V2")
    print(f"{'='*70}")

    header = f"{'Candidate':<20} | {'V1 Score':<10} | {'V1 Verdict':<10} | {'V2 Prob':<10} | {'V2 Verdict':<10}"
    print(header)
    print("-" * len(header))

    v2_map = {c.candidate_id: c for c in v2_result.candidates}
    for c1 in v1_result.candidates:
        c2 = v2_map.get(c1.candidate_id)
        v2_prob = f"{c2.answer_probability:.3f}" if c2 else "N/A"
        v2_verdict = c2.verdict if c2 else "N/A"
        print(
            f"{c1.candidate_id:<20} | {c1.final_score:<10.3f} | {c1.verdict:<10} | "
            f"{v2_prob:<10} | {v2_verdict:<10}"
        )

    print(f"\nV1 Diagnostics: {v1_result.diagnostics.model_dump()}")
    print(f"V2 Diagnostics: {v2_result.diagnostics.model_dump()}")
    print(f"V1 Verdict: {v1_result.verdict}")
    print(f"V2 Verdict: {v2_result.verdict}")


def main():
    mock_path = Path(__file__).parent / "data" / "mock_data_Q001.json"
    hpvd_result = load_hpvd_result(str(mock_path))

    cross_encoder = DummyCrossEncoder()

    v1_pipeline = V1Pipeline(cross_encoder)
    v2_pipeline = V2Pipeline(cross_encoder)

    v1_result = v1_pipeline.run(hpvd_result)
    v2_result = v2_pipeline.run(hpvd_result)

    print_comparison(v1_result, v2_result)


if __name__ == "__main__":
    main()
