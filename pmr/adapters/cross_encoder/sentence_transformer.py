from sentence_transformers import CrossEncoder

from pmr.core.interfaces import CrossEncoderPort
from pmr.core.errors import CrossEncoderError


class SentenceTransformerCrossEncoder(CrossEncoderPort):
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
        max_length: int = 512,
    ):
        try:
            self._model = CrossEncoder(
                model_name,
                device=device,
                max_length=max_length,
            )
        except Exception as exc:
            raise CrossEncoderError(f"Failed to load model '{model_name}': {exc}") from exc

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        pairs = [(query, text) for text in texts]
        try:
            raw_scores = self._model.predict(pairs)
        except Exception as exc:
            raise CrossEncoderError(f"Cross-encoder prediction failed: {exc}") from exc
        return self._normalize(raw_scores)

    @staticmethod
    def _normalize(scores: list[float]) -> list[float]:
        if not scores:
            return []
        lo, hi = min(scores), max(scores)
        if hi - lo < 1e-9:
            return [0.5] * len(scores)
        return [(s - lo) / (hi - lo) for s in scores]
