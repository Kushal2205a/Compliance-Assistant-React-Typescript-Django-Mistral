import logging
import time

import ollama
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .pipeline.config import ChunkingConfig, EmbeddingConfig, IndexingConfig, PipelineConfig
from .pipeline.indexing.service import IndexingService

logger = logging.getLogger(__name__)

config = PipelineConfig(
    chunking=ChunkingConfig(strategy="compliance"),
    embedding=EmbeddingConfig(model_name="all-MiniLM-L6-v2"),
    indexing=IndexingConfig(index_dir="index_cache"),
)
indexing_service = IndexingService(config)

MAX_CONTEXT_LEN = 3000


def build_prompt(query: str, context: str) -> str:
    return f"""
You are a compliance expert analyzing compliance documents.
Answer questions based ONLY on the provided context and ONLY if the query is related to SOC2 compliance.
If the query is not related to SOC2 compliance, respond with "Sorry, I can only answer questions related to SOC2 compliance."
**Important Compliance Guidelines:**
1. Always reference specific section numbers
2. Highlight potential compliance risks
3. Distinguish between requirements and recommendations
**Context:**
{context}
**Question:**
{query}
**Response Format:**
[Answer]
[Risk Level: High/Medium/Low]
""".strip()


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

        try:
            total_start = time.time()
            progress_steps: list[str] = []

            def progress_callback(msg: str) -> None:
                progress_steps.append(msg)
                logger.info("[Progress] %s", msg)

            logger.info("Step 1: Indexing document...")
            progress_callback("Step 1: Indexing document...")
            t1 = time.time()
            result = indexing_service.index_document(
                pdf_file, progress_callback=progress_callback
            )
            elapsed1 = time.time() - t1
            logger.info("Index + Load Time: %.2f sec", elapsed1)
            progress_callback(f"Index + Load Time: {elapsed1:.2f} sec")

            logger.info("Step 2: Retrieving relevant chunks...")
            progress_callback("Step 2: Retrieving relevant chunks...")
            t2 = time.time()
            search_results = indexing_service.search(result, query, k=3)
            top_chunks = indexing_service.get_chunk_texts(search_results)
            elapsed2 = time.time() - t2
            logger.info("Search Time: %.2f sec", elapsed2)
            progress_callback(f"Search Time: {elapsed2:.2f} sec")

            logger.info("Step 3: Preparing LLM prompt...")
            progress_callback("Step 3: Preparing LLM prompt...")
            context = "\n".join(top_chunks)
            if len(context) > MAX_CONTEXT_LEN:
                context = context[:MAX_CONTEXT_LEN].rsplit(" ", 1)[0]
            prompt = build_prompt(query, context)

            logger.info("Step 4: Querying Ollama/Mistral (streaming)...")
            progress_callback("Step 4: Querying Ollama/Mistral (streaming)...")
            t3 = time.time()

            def stream_ollama():
                try:
                    for chunk in ollama.generate(
                        model="mistral", prompt=prompt, stream=True
                    ):
                        yield chunk.get("response", "")
                except Exception as e:
                    logger.exception("Exception in streaming Ollama/Mistral")
                    yield f"\n[ERROR]: {str(e)}"

            response = StreamingHttpResponse(
                stream_ollama(), content_type="text/plain"
            )
            elapsed3 = time.time() - t3
            logger.info("Ollama Response Time: %.2f sec (streaming)", elapsed3)
            progress_callback(f"Ollama Response Time: {elapsed3:.2f} sec (streaming)")

            total_time = time.time() - total_start
            logger.info("TOTAL Request Time: %.2f sec (streaming)", total_time)
            progress_callback(
                f"TOTAL Request Time: {total_time:.2f} sec (streaming)"
            )

            return response

        except Exception as e:
            logger.exception("Exception in PDF QA endpoint")
            progress_steps.append(f"Exception: {str(e)}")
            return Response(
                {"error": str(e), "progress": progress_steps}, status=500
            )


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
