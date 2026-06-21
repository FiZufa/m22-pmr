from pmr.adapters.cross_encoder.dummy import DummyCrossEncoder

__all__ = [
    "DummyCrossEncoder",
    "SentenceTransformerCrossEncoder",
]


def SentenceTransformerCrossEncoder(*args, **kwargs):
    from pmr.adapters.cross_encoder.sentence_transformer import (
        SentenceTransformerCrossEncoder as _STCE,
    )
    return _STCE(*args, **kwargs)

