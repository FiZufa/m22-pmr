from __future__ import annotations

from abc import ABC, abstractmethod


class CrossEncoderPort(ABC):
    @abstractmethod
    def rerank(self, query: str, texts: list[str]) -> list[float]:
        ...
