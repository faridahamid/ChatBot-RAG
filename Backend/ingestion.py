# ingestion.py
import os
import uuid
from typing import List, Optional
import pandas as pd
from pypdf import PdfReader
import docx
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from models import Document, DocumentChunk


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
_embedder = SentenceTransformer(EMBEDDING_MODEL)




def _read_pdf(path: str) -> str:
    reader = PdfReader(path)
    return "\n".join([(p.extract_text() or "") for p in reader.pages])

def _read_docx(path: str) -> str:
    d = docx.Document(path)
    return "\n".join([para.text for para in d.paragraphs])

def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def _read_csv(path: str) -> str:
    df = pd.read_csv(path)
    df = df.fillna("")  
    lines = []
   
    for _, row in df.iterrows():
        line = " | ".join(f"{col}: {row[col]}" for col in df.columns)
        lines.append(line)
    return "\n".join(lines)


def extract_text(file_path: str, filetype: str) -> str:
   
    ft = (filetype or "").lower()
    if ft == "pdf":
        return _read_pdf(file_path)
    if ft == "docx":
        return _read_docx(file_path)
    if ft == "txt":
        return _read_txt(file_path)
    if ft == "csv":
        return _read_csv(file_path)
    raise ValueError(f"Unsupported file type: {filetype}")



def chunk_text(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
   
    text = (text or "").strip()
    if not text:
        return []
    chunks, i, n = [], 0, len(text)
    step = max(1, max_chars - overlap)
    while i < n:
        end = min(i + max_chars, n)
        piece = text[i:end].strip()
        if piece:
            chunks.append(piece)
        i += step
    return chunks

def embed_chunks(chunks: List[str]) -> List[List[float]]:
    if not chunks:
        return []
    
    return _embedder.encode(chunks, normalize_embeddings=True).tolist()

def embed_query(question: str) -> List[float]:
    return _embedder.encode([question], normalize_embeddings=True).tolist()[0]




def extract_text_from_raw(raw_text: Optional[str]) -> str:
    return (raw_text or "").strip()




def process_document(
    db: Session,
    org_id: str,
    user_id: str,
    file_path: str,
    filetype: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100
):
    
    
    text_all = extract_text(file_path, filetype)

    
    doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        uploaded_by=user_id,      
        filename=os.path.basename(file_path),
        filetype=filetype.lower()
    )
    db.add(doc)
    db.flush()  


    chunks = chunk_text(text_all, max_chars=chunk_size, overlap=chunk_overlap)

    vectors = embed_chunks(chunks)

   
    for content, vec in zip(chunks, vectors):
        db.add(DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            content=content,
            embedding=vec
        ))

    db.commit()
    return {"document_id": doc.id, "chunks": len(chunks)}
