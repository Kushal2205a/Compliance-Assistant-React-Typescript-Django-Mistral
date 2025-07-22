
import pdfplumber
import spacy
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import re
import hashlib
import os
import pickle


nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer("all-MiniLM-L6-v2")

# Directory for cache
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def file_hash(file) -> str:
    """Compute SHA256 hash of a file-like object (PDF)."""
    pos = file.tell()
    file.seek(0)
    hasher = hashlib.sha256()
    while True:
        chunk = file.read(8192)
        if not chunk:
            break
        hasher.update(chunk)
    file.seek(pos)
    return hasher.hexdigest()

def extract_compliance_metadata(text: str):
    sections = []
    current_section = ""
    
    for line in text.split("\n"):
        
        if re.match(r'^\d+\.\d+\s+', line):
            if current_section:
                sections.append(current_section)
            current_section = line
        elif current_section:
            current_section += '\n' + line
    
    
    if current_section:
        sections.append(current_section)
        
    return sections

def extract_text_from_pdf(file) -> str:
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def sliding_window_chunker(text: str, chunk_size: int = 150, overlap: int = 30):
    words = text.split()
    chunks = []

    for i in range(0, len(words), chunk_size - overlap):
        chunk = words[i: i + chunk_size]
        chunks.append(" ".join(chunk))
    return chunks

def compliance_chunker(text: str):
    sections = []
    current_section = ""
    
    for line in text.split("\n"): 
        
        if re.match(r'^\d+\.\d+\s+', line):
            if current_section:
                sections.append(current_section)
                current_section = line
            else:
                current_section = line
        elif current_section:
            current_section += '\n' + line

    if current_section:
        sections.append(current_section)
        
    final_chunks = []
    for section in sections:
        if len(section) <= 1500:
            final_chunks.append(section)
        else:
            doc = nlp(section)
            chunk = ""
            
            for sent in doc.sents:
                if len(chunk) + len(sent.text) > 1000:
                    final_chunks.append(chunk)
                    chunk = sent.text
                else:
                    chunk += ' ' + sent.text
                    
            if chunk:
                final_chunks.append(chunk)
                
    return final_chunks

def create_faiss_index(chunks: list[str]):
    embeddings = model.encode(chunks)
    embeddings = np.array(embeddings).astype("float32")
    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index, embeddings

# Main cache function
def get_cached_chunks_and_index(file, progress_callback=None):
    """
    Returns (chunks, index, progress_steps) for a PDF file, using cache if available.
    progress_callback: function to call with status string at each step.
    """
    def log(msg):
        if progress_callback:
            progress_callback(msg)
    hashval = file_hash(file)
    cache_path = os.path.join(CACHE_DIR, f"{hashval}.pkl")
    if os.path.exists(cache_path):
        log("Loaded from cache.")
        with open(cache_path, "rb") as f:
            data = pickle.load(f)
        return data["chunks"], data["index"], ["Loaded from cache."]
    # Not cached: extract, chunk, embed, cache
    log("Extracting text from PDF...")
    text_content = extract_text_from_pdf(file)
    log("Chunking text...")
    chunks = sliding_window_chunker(text_content)
    log("Creating embeddings and FAISS index...")
    index, _ = create_faiss_index(chunks)
    # Save to cache
    log("Saving to cache...")
    with open(cache_path, "wb") as f:
        pickle.dump({"chunks": chunks, "index": index}, f)
    return chunks, index, ["Extracted text", "Chunked text", "Created embeddings and index", "Saved to cache"]

def search_index(index, query: str, chunks: list[str], top_k=5):
    query_embedding = model.encode(query)
    query_embedding = np.array(query_embedding).astype("float32").reshape(1, -1)
    faiss.normalize_L2(query_embedding)

    D, I = index.search(query_embedding, top_k)
    return [chunks[i] for i in I[0]]