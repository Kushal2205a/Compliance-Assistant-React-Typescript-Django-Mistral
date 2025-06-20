import pdfplumber
import spacy
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer("all-MiniLM-L6-v2")

def extract_text_from_pdf(file) -> str:
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def sliding_window_chunker(text:str, chunk_size : int = 150, overlap : int = 30):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = words[i  : i + chunk_size]
        chunks.append(" ".join(chunk))
    return chunks

'''
def chunk_text(text: str) -> list[str]:
    doc = nlp(text)
    return [sent.text for sent in doc.sents if sent.text.strip()]
'''

def create_faiss_index(chunks: list[str]):
    embeddings = model.encode(chunks)
    embeddings = np.array(embeddings).astype("float32")
    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index, embeddings

def search_index(index, query: str, chunks: list[str], top_k=5):
    query_embedding = model.encode(query)
    query_embedding = np.array(query_embedding).astype("float32").reshape(1, -1)
    faiss.normalize_L2(query_embedding)

    D, I = index.search(query_embedding, top_k)
    return [chunks[i] for i in I[0]]
print("Debugging:", dir())
