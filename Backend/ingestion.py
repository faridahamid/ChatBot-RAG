# ingestion.py
import os
import uuid
import hashlib
import re
import io
from typing import List, Optional, Iterable
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

# In-memory readers ---------------------------------------------------------
def _read_pdf_bytes(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join([(p.extract_text() or "") for p in reader.pages])

def _read_docx_bytes(data: bytes) -> str:
    d = docx.Document(io.BytesIO(data))
    return "\n".join([para.text for para in d.paragraphs])

def _read_txt_bytes(data: bytes) -> str:
    return data.decode("utf-8", errors="ignore")

def _read_csv_bytes(data: bytes) -> str:
    df = pd.read_csv(io.BytesIO(data))
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

def extract_text_from_bytes(file_bytes: bytes, filetype: str) -> str:
    ft = (filetype or "").lower()
    if ft == "pdf":
        return _read_pdf_bytes(file_bytes)
    if ft == "docx":
        return _read_docx_bytes(file_bytes)
    if ft == "txt":
        return _read_txt_bytes(file_bytes)
    if ft == "csv":
        return _read_csv_bytes(file_bytes)
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

def embed_chunks_in_batches(chunks: List[str], batch_size: int = 64) -> List[List[float]]:
    if not chunks:
        return []
    embeddings: List[List[float]] = []
    total = len(chunks)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = chunks[start:end]
        vecs = _embedder.encode(batch, normalize_embeddings=True).tolist()
        embeddings.extend(vecs)
    return embeddings

def embed_query(question: str) -> List[float]:
    return _embedder.encode([question], normalize_embeddings=True).tolist()[0]




def extract_text_from_raw(raw_text: Optional[str]) -> str:
    return (raw_text or "").strip()


def _normalize_text_for_hash(text: str) -> str:
    # Lowercase, collapse whitespace, strip
    lowered = text.lower()
    collapsed = re.sub(r"\s+", " ", lowered)
    return collapsed.strip()


def _sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()




def process_document(
    db: Session,
    org_id: str,
    user_id: str,
    file_path: str,
    filetype: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    embedding_batch_size: int = 64,
    insert_batch_size: int = 200,
):
    #duplicate
    text_all = extract_text(file_path, filetype)
    normalized = _normalize_text_for_hash(text_all)
    content_hash = _sha256_hex(normalized)

   
    existing = (
        db.query(Document)
        .filter(Document.organization_id == org_id, Document.content_hash == content_hash)
        .first()
    )
    if existing is not None:
        
        raise ValueError("DUPLICATE_DOCUMENT")

    
    doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        uploaded_by=user_id,
        filename=os.path.basename(file_path),
        filetype=filetype.lower(),
        content_hash=content_hash,
    )
    db.add(doc)
    
    db.flush()
    db.commit()

    
    chunks = chunk_text(text_all, max_chars=chunk_size, overlap=chunk_overlap)

    
    total = len(chunks)
    for start in range(0, total, embedding_batch_size):
        end = min(start + embedding_batch_size, total)
        batch_texts = chunks[start:end]
        batch_vecs = _embedder.encode(batch_texts, normalize_embeddings=True).tolist()

        
        batch_objects: List[DocumentChunk] = [
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc.id,
                content=content,
                embedding=vec,
            )
            for content, vec in zip(batch_texts, batch_vecs)
        ]

        
        for i in range(0, len(batch_objects), insert_batch_size):
            slice_objs = batch_objects[i : i + insert_batch_size]
            if not slice_objs:
                continue
            db.bulk_save_objects(slice_objs)
            db.flush()
            db.commit()

    return {"document_id": doc.id, "chunks": total}


def process_document_from_bytes(
    db: Session,
    org_id: str,
    user_id: str,
    file_bytes: bytes,
    filename: str,
    filetype: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    embedding_batch_size: int = 64,
    insert_batch_size: int = 200,
):
    # Read and hash full text for duplicate detection
    text_all = extract_text_from_bytes(file_bytes, filetype)
    normalized = _normalize_text_for_hash(text_all)
    content_hash = _sha256_hex(normalized)

    # Check duplicate per organization
    existing = (
        db.query(Document)
        .filter(Document.organization_id == org_id, Document.content_hash == content_hash)
        .first()
    )
    if existing is not None:
        raise ValueError("DUPLICATE_DOCUMENT")

    # Create Document row
    doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        uploaded_by=user_id,
        filename=filename,
        filetype=filetype.lower(),
        content_hash=content_hash,
    )
    db.add(doc)
    db.flush()
    db.commit()

    # Chunk
    chunks = chunk_text(text_all, max_chars=chunk_size, overlap=chunk_overlap)
    total = len(chunks)

    # Embed and insert per batch
    for start in range(0, total, embedding_batch_size):
        end = min(start + embedding_batch_size, total)
        batch_texts = chunks[start:end]
        batch_vecs = _embedder.encode(batch_texts, normalize_embeddings=True).tolist()

        # Insert this embedding batch in smaller DB batches
        batch_objects: List[DocumentChunk] = [
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc.id,
                content=content,
                embedding=vec,
            )
            for content, vec in zip(batch_texts, batch_vecs)
        ]
        for i in range(0, len(batch_objects), insert_batch_size):
            slice_objs = batch_objects[i : i + insert_batch_size]
            if not slice_objs:
                continue
            db.bulk_save_objects(slice_objs)
            db.flush()
            db.commit()

    return {"document_id": doc.id, "chunks": total}
