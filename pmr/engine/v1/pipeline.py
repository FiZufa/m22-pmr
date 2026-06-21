from __future__ import annotations

import time

from pmr.core.interfaces import CrossEncoderPort
from pmr.core.models import HPVDResult, PMRResult
from pmr.engine.v1.semantic import run_semantic_assessment
from pmr.engine.v1.threshold import filter_by_threshold
from pmr.engine.v1.scoring import apply_domain_scoring
from pmr.engine.v1.verdict import run_verdict_engine
from pmr.config.v1_defaults import V1_DEFAULTS


class V1Pipeline:
    def __init__(
        self,
        cross_encoder: CrossEncoderPort,
        config: dict | None = None,
    ):
        self._cross_encoder = cross_encoder
        self._config = config or V1_DEFAULTS

    def run(self, hpvd_result: HPVDResult) -> PMRResult:
        start = time.perf_counter()

        scored = run_semantic_assessment(hpvd_result, self._cross_encoder)

        before_filter = len(scored)
        filtered = filter_by_threshold(scored, self._config["semantic_threshold"])
        dropped = before_filter - len(filtered)

        domain_scored = apply_domain_scoring(filtered, hpvd_result, self._config)

        result = run_verdict_engine(
            domain_scored,
            hpvd_result,
            self._config,
            dropped_before=dropped,
            cross_encoder_name=type(self._cross_encoder).__name__,
        )

        result.diagnostics.reranking_latency_ms = (time.perf_counter() - start) * 1000
        return result
