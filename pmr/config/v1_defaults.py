V1_DEFAULTS = {
    "current_tenant_id": "claims",
    "current_department": "finance",
    "semantic_threshold": 0.45,
    "final_threshold": 0.75,
    "weights": {
        "semantic": 0.40,
        "department": 0.20,
        "tenant": 0.15,
        "trust": 0.10,
        "completeness": 0.05,
        "confidence": 0.10,
    },
    "department_match": {
        "same": 1.0,
        "related": 0.6,
        "unrelated": 0.0,
        "related_pairs": [
            ["operations", "logistics"],
            ["sales", "product"],
            ["hr", "operations"],
            ["finance", "operations"],
            ["support", "operations"],
        ],
    },
    "tenant_priority": {
        "same": 1.0,
        "global": 0.6,
        "other": 0.0,
    },
    "source_trust": {
        "official_policy": 1.0,
        "sop_repository": 0.9,
        "product_catalog": 0.85,
        "knowledge_base": 0.8,
        "wiki": 0.6,
        "chat_transcript": 0.3,
    },
    "confidence_weights": {
        "rrf": 0.40,
        "bm25": 0.30,
        "vector": 0.30,
    },
}
