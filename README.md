# Compliance QnA Assistant 🏛️🔍

![React](https://img.shields.io/badge/Frontend-React_TypeScript-61DAFB)
![Django](https://img.shields.io/badge/Backend-Django_REST-092E20)
![Mistral](https://img.shields.io/badge/LLM-Mistral_7B-purple)
![FAISS](https://img.shields.io/badge/Semantic_Search-FAISS-orange)

An AI-powered compliance assistant that answers questions from uploaded PDF documents using Mistral 7B and FAISS vector search.

![Demo Screenshot](https://via.placeholder.com/800x500?text=Compliance+QnA+Assistant+Demo)

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

## Installation 🚀

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
