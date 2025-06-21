from rest_framework.views import APIView 
from rest_framework.response import Response 
from rest_framework.parsers import MultiPartParser, FormParser 
from rest_framework import status 
from .embeddings import extract_text_from_pdf, sliding_window_chunker, create_faiss_index, search_index
import ollama
from datetime import date 

def query_mistral(prompt: str):
    
    response = ollama.generate(model='mistral', prompt=prompt)
    return response['response']

class viewQueryPDF(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        query = request.data.get("query")
        pdf_file = request.data.get("pdf")

        if not query or not pdf_file:
            return Response({"error": "Missing query or PDF"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
        
            text_content = extract_text_from_pdf(pdf_file)
            
        
            chunks = sliding_window_chunker(text_content)
            
            
            index, _ = create_faiss_index(chunks)
            top_chunks = search_index(index, query, chunks)
            
        
            context = "\n".join(top_chunks)
            
            
            prompt = f"""
                                You are a compliance expert analyzing compliance documents. 
                                Answer questions based ONLY on the provided context. 

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
           
            answer = query_mistral(prompt)

            return Response({"answer": answer}, status=200)
        
        except Exception as e:
            return Response({"error": str(e)}, status=500)