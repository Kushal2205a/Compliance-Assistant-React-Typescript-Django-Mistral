import numpy as np

from .pipeline.config import ChunkingConfig, EmbeddingConfig, IndexingConfig, PipelineConfig
from .pipeline.indexing.service import IndexingService

config = PipelineConfig(
    chunking=ChunkingConfig(strategy="compliance"),
    embedding=EmbeddingConfig(model_name="all-MiniLM-L6-v2"),
    indexing=IndexingConfig(index_dir="index_cache"),
)
indexing_service = IndexingService(config)

test_queries = [
    {
        "query": "What commitments does Atlassian make regarding Security?",
        "relevant": [
            "Atlassian will implement and maintain physical, technical, and administrative security measures"
        ],
    },
    {
        "query": "What is Atlassian's availability guarantee for Jira Align?",
        "relevant": [
            "Jira Align: Atlassian will use commercially reasonable efforts to make Jira Align available at least 99.5% of the time"
        ],
    },
    {
        "query": "How does Atlassian classify sensitive information?",
        "relevant": [
            "Data Classification",
            "Restricted Information",
            "Confidential Information",
        ],
    },
    {
        "query": "What encryption standards are used by Atlassian?",
        "relevant": [
            "Advanced Encryption Standard (AES) 256",
            "TLS 1.2 or higher",
        ],
    },
    {
        "query": "What are Atlassian's incident response policies?",
        "relevant": [
            "Atlassian maintains a company-wide incident management policy",
            "incident management response procedures",
        ],
    },
    {
        "query": "Which subservice organizations does Atlassian use?",
        "relevant": ["AWS", "Azure", "MongoDB"],
    },
    {
        "query": "What responsibilities do user entities have under CC6.1?",
        "relevant": [
            "User entities are responsible for configuring their own instance, including logical security and privacy settings"
        ],
    },
    {
        "query": "How long does Atlassian retain backups?",
        "relevant": ["Backups are retained for a minimum of 30 days"],
    },
    {
        "query": "Who at Atlassian oversees access controls and compliance?",
        "relevant": ["Trust group", "Chief Trust Officer"],
    },
    {
        "query": "What availability guarantee is provided for JSM Operations?",
        "relevant": [
            "JSM Operations: Atlassian will use commercially reasonable efforts to make JSM Operations available at least 99.9% of the time"
        ],
    },
    {
        "query": "What availability guarantee does Jira Align provide?",
        "relevant": ["99.5% of the time", "Jira Align availability"],
    },
    {
        "query": "What availability guarantee does JSM Operations provide?",
        "relevant": ["99.9% of the time", "JSM Operations availability"],
    },
    {
        "query": "How long does Atlassian retain customer data after termination?",
        "relevant": [
            "retains data for up to 60 days",
            "archive for at least 30 days",
        ],
    },
    {
        "query": "What cryptographic method is used for encryption at rest?",
        "relevant": ["AES 256", "encryption at rest"],
    },
    {
        "query": "Who is responsible for risk management?",
        "relevant": ["Enterprise Risk Management", "Risk Management policy"],
    },
]


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for r in top_k if any(rel.lower() in r.lower() for rel in relevant))
    return hits / k


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    if not relevant:
        return 0.0
    hits = sum(1 for r in top_k if any(rel.lower() in r.lower() for rel in relevant))
    return hits / len(relevant)


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    for i, r in enumerate(retrieved):
        if any(rel.lower() in r.lower() for rel in relevant):
            return 1.0 / (i + 1)
    return 0.0


def run_evaluation(pdf_path: str) -> None:
    with open(pdf_path, "rb") as f:
        result = indexing_service.index_document(f)

    results = []
    for t in test_queries:
        query = t["query"]
        relevant = t["relevant"]
        search_results = indexing_service.search(result, query, k=5)
        retrieved = indexing_service.get_chunk_texts(search_results)[:5]

        results.append(
            {
                "P@3": precision_at_k(retrieved, relevant, 3),
                "R@3": recall_at_k(retrieved, relevant, 3),
                "MRR": mrr(retrieved, relevant),
            }
        )

    avg_p3 = np.mean([r["P@3"] for r in results])
    avg_r3 = np.mean([r["R@3"] for r in results])
    avg_mrr = np.mean([r["MRR"] for r in results])

    print("Retrieval Evaluation Results:")
    print(f"Precision@3: {avg_p3:.2f}")
    print(f"Recall@3: {avg_r3:.2f}")
    print(f"MRR: {avg_mrr:.2f}")


if __name__ == "__main__":
    run_evaluation("compliance.pdf")
