import numpy as np
from evaluation import evaluate_query
from embeddings import get_cached_chunks_and_index, search_index

# Example gold standard queries
test_queries = [
    {
        "query": "What commitments does Atlassian make regarding Security?",
        "relevant": ["Atlassian will implement and maintain physical, technical, and administrative security measures"]
    },
    {
        "query": "What is Atlassian's availability guarantee for Jira Align?",
        "relevant": ["Jira Align: Atlassian will use commercially reasonable efforts to make Jira Align available at least 99.5% of the time"]
    },
    {
        "query": "How does Atlassian classify sensitive information?",
        "relevant": ["Data Classification", "Restricted Information", "Confidential Information"]
    },
    {
        "query": "What encryption standards are used by Atlassian?",
        "relevant": ["Advanced Encryption Standard (AES) 256", "TLS 1.2 or higher"]
    },
    {
        "query": "What are Atlassian’s incident response policies?",
        "relevant": ["Atlassian maintains a company-wide incident management policy", "incident management response procedures"]
    },
    {
        "query": "Which subservice organizations does Atlassian use?",
        "relevant": ["AWS", "Azure", "MongoDB"]
    },
    {
        "query": "What responsibilities do user entities have under CC6.1?",
        "relevant": ["User entities are responsible for configuring their own instance, including logical security and privacy settings"]
    },
    {
        "query": "How long does Atlassian retain backups?",
        "relevant": ["Backups are retained for a minimum of 30 days"]
    },
    {
        "query": "Who at Atlassian oversees access controls and compliance?",
        "relevant": ["Trust group", "Chief Trust Officer"]
    },
    {
        "query": "What availability guarantee is provided for JSM Operations?",
        "relevant": ["JSM Operations: Atlassian will use commercially reasonable efforts to make JSM Operations available at least 99.9% of the time"]
    },
    
    {
        "query": "What availability guarantee does Jira Align provide?",
        "relevant": ["99.5% of the time", "Jira Align availability"]
    },
    {
        "query": "What availability guarantee does JSM Operations provide?",
        "relevant": ["99.9% of the time", "JSM Operations availability"]
    },
    {
        "query": "How long does Atlassian retain customer data after termination?",
        "relevant": ["retains data for up to 60 days", "archive for at least 30 days"]
    },
    {
        "query": "What cryptographic method is used for encryption at rest?",
        "relevant": ["AES 256", "encryption at rest"]
    },
    {
        "query": "Who is responsible for risk management?",
        "relevant": ["Enterprise Risk Management", "Risk Management policy"]
    }
]


def run_evaluation(pdf_path):
    with open(pdf_path, "rb") as f:   # ✅ give file object instead of string
        chunks, index, _ = get_cached_chunks_and_index(f)

    results = []
    for t in test_queries:
        query = t["query"]
        relevant = t["relevant"]

        retrieved = search_index(index, query, chunks)[:5]
        metrics = evaluate_query(query, retrieved, relevant, k=3)
        results.append(metrics)

    avg_p3 = np.mean([r["P@3"] for r in results])
    avg_r3 = np.mean([r["R@3"] for r in results])
    avg_mrr = np.mean([r["MRR"] for r in results])

    print("📊 Retrieval Evaluation Results:")
    print(f"Precision@3: {avg_p3:.2f}")
    print(f"Recall@3: {avg_r3:.2f}")
    print(f"MRR: {avg_mrr:.2f}")

if __name__ == "__main__":
    run_evaluation("C:/Users/Kushal/Documents/New/Compliance-Assistant-React-Typescript-Django-Mistral/backend/rag/compliance.pdf")  # replace with your PDF path
