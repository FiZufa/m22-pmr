from __future__ import annotations

import time

from pmr.core.interfaces import CrossEncoderPort
from pmr.core.models import HPVDResult, PMRResult
from pmr.engine.v2.evidence import extract_evidence
from pmr.engine.v2.semantic import run_semantic_assessment
from pmr.engine.v2.gate import apply_semantic_gate
from pmr.engine.v2.scoring import apply_domain_scoring
from pmr.engine.v2.confidence import apply_confidence_assessment
from pmr.engine.v2.fusion import run_probability_fusion
from pmr.engine.v2.verdict import run_verdict_engine
from pmr.config.v2_defaults import V2_DEFAULTS


class V2Pipeline:
    def __init__(
        self,
        cross_encoder: CrossEncoderPort,
        config: dict | None = None,
    ):
        self._cross_encoder = cross_encoder
        self._config = config or V2_DEFAULTS

    def run(self, hpvd_result: HPVDResult) -> PMRResult:
        start = time.perf_counter()

        extract_evidence(hpvd_result)

        scored = run_semantic_assessment(hpvd_result, self._cross_encoder)

        gate_result = apply_semantic_gate(scored, self._config["semantic_threshold"])

        domain_scored = apply_domain_scoring(
            gate_result.passed, hpvd_result, self._config
        )

        confident = apply_confidence_assessment(domain_scored, self._config)

        fused = run_probability_fusion(confident, self._config)

        result = run_verdict_engine(
            gated_count=len(gate_result.gated),
            passed=fused,
            gated=gate_result.gated,
            hpvd_result=hpvd_result,
            config=self._config,
            cross_encoder_name=type(self._cross_encoder).__name__,
        )

        result.diagnostics.reranking_latency_ms = (time.perf_counter() - start) * 1000
        return result
