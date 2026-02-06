# Compliance QnA Assistant 

![React](https://img.shields.io/badge/Frontend-React_TypeScript-61DAFB)
![Django](https://img.shields.io/badge/Backend-Django_REST-092E20)
![Mistral](https://img.shields.io/badge/LLM-Mistral_7B-purple)
![FAISS](https://img.shields.io/badge/Semantic_Search-FAISS-orange)

An AI-powered compliance assistant that answers questions from uploaded PDF documents using Mistral 7B and FAISS vector search.
![image](https://github.com/user-attachments/assets/366f08c7-31db-4103-8cd9-7c49bc4699e8)

## Why this is not a regular “PDF RAG” 

Most PDF RAG's stop at: chunk PDF -> embed -> retrieve -> generate.
This project is built more like a compliance assistant.

### 1) Domain guardrails (SOC2 only)
The assistant is scoped to SOC2 style compliance questions. If the question is outside scope, it refuses instead of guessing.

### 2) Compliance style answers, not freeform chat
Responses follow a fixed format and include:
- an explicit answer
- a risk level (High / Medium / Low)
- section references (so you can verify quickly)

### 3) Streaming, end to end
The backend streams tokens from the model and the React UI renders the answer as it arrives, so it feels instant on long responses.

### 4) Fast repeat queries with caching
For the same PDF, the app does not rebuild embeddings every time.
It uses a SHA256 hash of the uploaded file to cache:
- extracted chunks
- the FAISS index

### 5) Retrieval tuned for structured compliance docs
Along with a basic chunker, the codebase includes a compliance focused section chunker that:
- detects numbered sections (like 4.2, 6.1)
- splits long sections by sentences for cleaner chunks

### 6) Observability and basic evaluation hooks
The API logs step timings (index load, search time, model time) and includes seed test queries you can expand into an evaluation set later.

## Features 

- **Document Intelligence**  
  - PDF text extraction with metadata parsing
  - Section-aware chunking for compliance documents
  - FAISS vector search for precise answers

- **AI-Powered Q&A**  
  - Mistral 7B for regulatory analysis
  - Risk level assessment (High/Medium/Low)
  - Section reference tracking

- **Modern Interface**  
  - Type safe React frontend
  - Tailwind CSS styling
  - Responsive chat interface

## Tech Stack 

| Component          | Technology               |
|--------------------|--------------------------|
| **Frontend**       | React + TypeScript       |
| **Styling**        | Tailwind CSS             |
| **Backend**        | Django REST Framework    |
| **Vector Search**  | FAISS                    |
| **LLM**           | Mistral 7B via Ollama    |
| **PDF Processing** | pdfplumber + spaCy       |

## Installation 

### Backend Setup (Django)
```bash
# Clone repository
git clone https://github.com/yourusername/compliance-qna-assistant.git
cd compliance-qna-assistant/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run Ollama (in separate terminal)
ollama pull mistral
ollama serve

# Start Django server
python manage.py runserver
