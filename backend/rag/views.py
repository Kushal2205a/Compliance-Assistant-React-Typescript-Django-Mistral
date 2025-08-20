from rest_framework.views import APIView 
from rest_framework.response import Response 
from rest_framework.parsers import MultiPartParser, FormParser 
from rest_framework import status 
from .embeddings import get_cached_chunks_and_index, search_index
import ollama
from datetime import date 
import time
import logging
from django.http import StreamingHttpResponse
logger = logging.getLogger(__name__)
import numpy as np 

def query_mistral(prompt: str):
    
    response = ollama.generate(model='mistral', prompt=prompt)
    return response['response']

class viewQueryPDF(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        query = request.data.get("query")
        pdf_file = request.data.get("pdf")

        if not query or not pdf_file:
            logger.error("Missing query or PDF in request.")
            return Response({"error": "Missing query or PDF"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            total_start = time.time()
            progress_steps = []

            def progress_callback(msg):
                progress_steps.append(msg)
                logger.info(f"[Progress] {msg}")

            logger.info("Step 1: Caching chunks + building/loading FAISS index...")
            progress_callback("Step 1: Caching chunks + building/loading FAISS index...")
            t1 = time.time()
            chunks, index, _ = get_cached_chunks_and_index(pdf_file, progress_callback=progress_callback)
            elapsed1 = time.time() - t1
            logger.info(f"Chunks + Index Load Time: {elapsed1:.2f} sec")
            progress_callback(f"Chunks + Index Load Time: {elapsed1:.2f} sec")

            logger.info("Step 2: Semantic search in FAISS...")
            progress_callback("Step 2: Semantic search in FAISS...")
            t2 = time.time()
            top_chunks = search_index(index, query, chunks)
            elapsed2 = time.time() - t2
            logger.info(f"FAISS Search Time: {elapsed2:.2f} sec")
            progress_callback(f"FAISS Search Time: {elapsed2:.2f} sec")

            logger.info("Step 3: Preparing LLM prompt...")
            progress_callback("Step 3: Preparing LLM prompt...")
            context = "\n".join(top_chunks)
            max_context_len = 3000
            if len(context) > max_context_len:
                context = context[:max_context_len].rsplit(' ', 1)[0]
            prompt = f"""
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
            """

            logger.info("Step 4: Querying Ollama/Mistral (streaming)...")
            progress_callback("Step 4: Querying Ollama/Mistral (streaming)...")
            t3 = time.time()

            def stream_ollama():
                try:
                    # Use Ollama's streaming API
                    for chunk in ollama.generate(model='mistral', prompt=prompt, stream=True):
                        # Each chunk is a dict with 'response' key
                        yield chunk.get('response', '')
                except Exception as e:
                    logger.exception("❌ Exception in streaming Ollama/Mistral")
                    yield f"\n[ERROR]: {str(e)}"

            response = StreamingHttpResponse(stream_ollama(), content_type='text/plain')
            elapsed3 = time.time() - t3
            logger.info(f"Ollama Response Time: {elapsed3:.2f} sec (streaming)")
            progress_callback(f"Ollama Response Time: {elapsed3:.2f} sec (streaming)")

            total_time = time.time() - total_start
            logger.info(f"✅ TOTAL Request Time: {total_time:.2f} sec (streaming)")
            progress_callback(f"✅ TOTAL Request Time: {total_time:.2f} sec (streaming)")

            return response

        except Exception as e:
            logger.exception("❌ Exception in PDF QA endpoint")
            progress_steps.append(f"❌ Exception: {str(e)}")
            return Response({"error": str(e), "progress": progress_steps}, status=500)
test_queries = [
    {
        "query": "What is clause 4.2 about?",
        "relevant": ["Clause 4.2 Data Retention"]  # gold truth
    },
    {
        "query": "Who is responsible for SOC2 audits?",
        "relevant": ["Section 6.1 Audit Responsibility"]
    }
]
