# main.py
import os
import uuid
import shutil
from typing import List

from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
from fastapi.responses import HTMLResponse


from database import get_db
from models import Organization, User, DocumentChunk
from schemas import OrgCreate, UserCreate, UploadResponse, AskRequest, AskResponse
from ingestion import process_document, process_document_from_bytes, embed_query

app = FastAPI(title="Multi-Org RAG Backend")


from database import engine

@app.on_event("startup")
def _ensure_indexes():
    with engine.begin() as conn:
        # Add column if missing
        conn.execute(text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name='documents' AND column_name='content_hash'
                ) THEN
                    ALTER TABLE documents ADD COLUMN content_hash TEXT;
                END IF;
            END $$;
            """
        ))
        
        conn.execute(text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_documents_org_hash
            ON documents (organization_id, content_hash);
            """
        ))



@app.post("/orgs", response_model=dict)
def create_org(payload: OrgCreate, db: Session = Depends(get_db)):
    org = Organization(name=payload.name, description=payload.description)
    db.add(org)
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name}



@app.post("/users", response_model=dict)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    
    user = User(
        username=payload.username,
        password_hash=payload.password,
        role=payload.role,
        organization_id=payload.organization_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username}



@app.post("/upload", response_model=UploadResponse)
def upload_document(
    org_id: uuid.UUID = Form(...),
    user_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    filetype = file.filename.split(".")[-1]
    file_bytes = file.file.read()
    try:
        result = process_document_from_bytes(
            db=db,
            org_id=str(org_id),
            user_id=str(user_id),
            file_bytes=file_bytes,
            filename=file.filename,
            filetype=filetype,
        )
    except ValueError as e:
        if str(e) == "DUPLICATE_DOCUMENT":
            raise HTTPException(status_code=409, detail="Duplicate document for this organization")
        raise

    return UploadResponse(**result)



@app.post("/ask", response_model=AskResponse)
def ask_question(payload: AskRequest, db: Session = Depends(get_db)):
    query_vec = embed_query(payload.question)
    query_vec_np = np.array(query_vec, dtype=np.float32)

    sql = text("""
        SELECT 
            document_chunks.content,
            1 - (document_chunks.embedding <=> :query_vec) AS score
        FROM document_chunks
        JOIN documents ON documents.id = document_chunks.document_id
        WHERE documents.organization_id = :org_id
        ORDER BY document_chunks.embedding <=> :query_vec
        LIMIT 5
    """)

    rows = db.execute(sql, {
        "query_vec": query_vec_np.tolist(),
        "org_id": str(payload.org_id)
    }).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No matches found")

    top_snippets = [r.content for r in rows]
    top_scores = [float(r.score) for r in rows]

    return AskResponse(
        answer_preview=top_snippets[0],
        top_scores=top_scores,
        top_snippets=top_snippets
    )


@app.get("/")
def health_check():
    return {"status": "ok", "message": "RAG backend is running"}

@app.get("/test", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
  <body>
    <h2>Upload Test</h2>
    <form id="uploadForm" enctype="multipart/form-data" method="post" action="/upload">
      <input type="text" name="org_id" placeholder="Organization ID" required><br><br>
      <input type="text" name="user_id" placeholder="User ID" required><br><br>
      <input type="file" name="file" required><br><br>
      <button type="submit">Upload</button>
    </form>
  </body>
</html>
    """
