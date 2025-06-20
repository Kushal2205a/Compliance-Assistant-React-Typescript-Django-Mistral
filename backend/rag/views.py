from django.shortcuts import render
from rest_framework.views import APIView 
from rest_framework.response import Response 
from rest_framework.parsers import MultiPartParser , FormParser 
from rest_framework import status 
from transformers import pipeline 
from .embeddings import extract_text_from_pdf, sliding_window_chunker, create_faiss_index, search_index
import os 
from django.conf import settings
import requests
import ollama

def query_mistral(prompt : str):
    response = ollama.generate(model='mistral', prompt=prompt)
    return response['response']
    


qa = pipeline("question-answering", model = "deepset/roberta-base-squad2")


class viewQueryPDF(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self , request):
        query = request.data.get("query")
        pdf_file = request.data.get("pdf")

        if not query or not pdf_file:
            return Response({"error" : "Missing query or PDF "} , status = status.HTTP_400_BAD_REQUEST)
        
        try:
            text = extract_text_from_pdf(pdf_file)

            chunks = sliding_window_chunker(text)
            index, _ = create_faiss_index(chunks)

            top_chunks = search_index(index , query , chunks )
            
            context = "\n".join(top_chunks)
            prompt = f"Answer the question based only on the context below. \n\nContext:\n {context}\n\n Question : {query}"
            answer = query_mistral(prompt)

            return Response({"answer" : answer} , status = 200)
        
        except Exception as e :
            return Response({"error" : str(e)}, status = 500)
        
    

