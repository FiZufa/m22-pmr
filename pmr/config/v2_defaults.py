V2_DEFAULTS = {
    "current_tenant_id": "claims",
    "semantic_threshold": 0.45,
    "probability_threshold": 0.75,
    "weights": {
        "semantic": 0.35,
        "business": 0.20,
        "tenant": 0.15,
        "trust": 0.10,
        "completeness": 0.05,
        "confidence": 0.15,
    },
    "tenant_priority": {
        "same": 1.0,
        "global": 0.6,
        "other": 0.0,
    },
    "source_trust": {
        "official_policy": 1.0,
        "sop_repository": 0.9,
        "knowledge_base": 0.8,
        "wiki": 0.6,
        "chat_transcript": 0.3,
    },
    "confidence_weights": {
        "rrf": 0.25,
        "bm25": 0.20,
        "vector": 0.25,
        "semantic": 0.30,
    },
}
