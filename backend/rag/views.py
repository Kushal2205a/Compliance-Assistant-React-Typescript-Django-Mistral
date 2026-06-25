import json
import logging

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from orchestration.service import OrchestrationService
from rag.pipeline.config import (
    AgentConfig,
    ChunkingConfig,
    EmbeddingConfig,
    GenerationConfig,
    IndexingConfig,
    LLMConfig,
    ObservabilityConfig,
    PipelineConfig,
    RetrievalConfig,
    RoutingConfig,
)

logger = logging.getLogger(__name__)

config = PipelineConfig(
    llm=LLMConfig(provider="ollama", model="mistral"),
    chunking=ChunkingConfig(strategy="compliance"),
    embedding=EmbeddingConfig(model_name="all-MiniLM-L6-v2"),
    indexing=IndexingConfig(index_dir="index_cache"),
    routing=RoutingConfig(enabled=True),
    retrieval=RetrievalConfig(top_k=5, enable_hybrid=False),
    generation=GenerationConfig(max_context_len=3000),
    agent=AgentConfig(max_retries=2, max_hops=3),
    observability=ObservabilityConfig(enabled=True),
)

orchestration = OrchestrationService(config)


class viewQueryPDF(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        query = request.data.get("query")
        pdf_file = request.data.get("pdf")

        if not query or not pdf_file:
            logger.error("Missing query or PDF in request.")
            return Response(
                {"error": "Missing query or PDF"}, status=status.HTTP_400_BAD_REQUEST
            )

        result = orchestration.process_query(query, pdf_file)

        response_data = {
            "response": result.response,
            "trace": result.trace.to_dict() if result.trace else None,
        }

        if result.errors:
            response_data["errors"] = result.errors
            return Response(response_data, status=500)

        return Response(response_data)


test_queries = [
    {
        "query": "What is clause 4.2 about?",
        "relevant": ["Clause 4.2 Data Retention"],
    },
    {
        "query": "Who is responsible for SOC2 audits?",
        "relevant": ["Section 6.1 Audit Responsibility"],
    },
]
