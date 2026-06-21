from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from pmr.core.interfaces import CrossEncoderPort
from pmr.core.models import HPVDResult, PMRResult
from pmr.engine.v1.pipeline import V1Pipeline
from pmr.engine.v2.pipeline import V2Pipeline
from pmr.config.api_config import API_CONFIG


def _build_cross_encoder(cfg: dict) -> CrossEncoderPort:
    encoder_type = cfg["type"]
    if encoder_type == "sentence_transformer":
        from pmr.adapters.cross_encoder.sentence_transformer import (
            SentenceTransformerCrossEncoder,
        )
        return SentenceTransformerCrossEncoder(
            model_name=cfg.get("model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            device=cfg.get("device", "cpu"),
        )
    from pmr.adapters.cross_encoder import DummyCrossEncoder
    return DummyCrossEncoder()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ce_cfg = API_CONFIG["cross_encoder"]
    cross_encoder = _build_cross_encoder(ce_cfg)
    app.state.cross_encoder = cross_encoder
    app.state.cross_encoder_type = ce_cfg["type"]
    app.state.cross_encoder_model = ce_cfg.get("model_name", "")
    app.state.v1_pipeline = V1Pipeline(cross_encoder)
    app.state.v2_pipeline = V2Pipeline(cross_encoder)
    yield


app = FastAPI(
    title="PMR API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return JSONResponse({
        "status": "ok",
        "cross_encoder": app.state.cross_encoder_type,
        "model": app.state.cross_encoder_model,
    })


@app.post("/v1/rank", response_model=PMRResult)
def rank_v1(hpvd_result: HPVDResult) -> PMRResult:
    return app.state.v1_pipeline.run(hpvd_result)


@app.post("/v2/rank", response_model=PMRResult)
def rank_v2(hpvd_result: HPVDResult) -> PMRResult:
    return app.state.v2_pipeline.run(hpvd_result)
