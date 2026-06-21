from pmr.core.interfaces import CrossEncoderPort


class DummyCrossEncoder(CrossEncoderPort):
    def __init__(self, scores: list[float] | None = None):
        self._scores = scores or [0.9, 0.8, 0.6, 0.3, 0.2]

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        scores = self._scores[:len(texts)]
        if len(scores) < len(texts):
            scores.extend([0.5] * (len(texts) - len(scores)))
        return scores[:len(texts)]
