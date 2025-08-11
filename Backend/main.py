# main.py
import os
import uuid
import shutil
from typing import List

from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from database import get_db, engine
from models import Organization, User, DocumentChunk, Document, Chat, ChatMessage
from schemas import OrgCreate, UserCreate, UploadResponse, AskRequest, AskResponse
from ingestion import process_document, process_document_from_bytes, embed_query
from llm import get_gemini, make_prompt
from admin_auth import router as admin_router

# Create single FastAPI app instance
app = FastAPI(title="Multi-Org RAG Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include admin router
app.include_router(admin_router)

# ========================================
# FRONTEND ROUTES
# ========================================

@app.get("/", response_class=HTMLResponse)
def welcome_page():
    """Serve the welcome page"""
    try:
        with open("Frontend/pages/welcome.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Welcome page not found</h1>", status_code=404)

@app.get("/login", response_class=HTMLResponse)
def login_page():
    """Serve the login page"""
    try:
        with open("Frontend/pages/login.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Login page not found</h1>", status_code=404)

@app.get("/admin-register", response_class=HTMLResponse)
def admin_register_page():
    """Serve the admin registration page"""
    try:
        with open("Frontend/pages/admin_register.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin registration page not found</h1>", status_code=404)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    """Serve the dashboard page"""
    try:
        with open("Frontend/pages/dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard page not found</h1>", status_code=404)

@app.get("/admin-upload", response_class=HTMLResponse)
def admin_upload_page():
    """Serve the admin upload page"""
    try:
        with open("Frontend/pages/admin_upload.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin upload page not found</h1>", status_code=404)

@app.get("/admin-users", response_class=HTMLResponse)
def admin_users_page():
    """Serve the admin user management page"""
    try:
        with open("Frontend/pages/admin_users.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin users page not found</h1>", status_code=404)

# ========================================
# STATIC FILES ROUTES
# ========================================

@app.get("/css/{filename}")
def get_css(filename: str):
    """Serve CSS files"""
    try:
        return FileResponse(f"Frontend/css/{filename}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="CSS file not found")

@app.get("/js/{filename}")
def get_js(filename: str):
    """Serve JavaScript files"""
    try:
        return FileResponse(f"Frontend/js/{filename}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="JavaScript file not found")

# ========================================
# API ENDPOINTS
# ========================================

@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    # Enforce that only non-admin users can ask, and they must belong to the org
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(payload.org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    if (user.role or "").lower() != "user":
        return AskResponse(answer="You are an admin; you can't ask questions in this interface.")

    # Embed query
    qvec = embed_query(payload.question)
    qvec_np = np.array(qvec, dtype=np.float32)

    # Retrieve top-k via pgvector distance operator `<=>` (lower is closer)
    top_k = int(os.getenv("RAG_TOP_K", "5"))
    sql = text(
        f"""
        SELECT 
            dc.id AS chunk_id,
            dc.content AS content,
            d.filename AS filename,
            (dc.embedding <=> (:q)::vector) AS distance
        FROM document_chunks AS dc
        JOIN documents AS d ON d.id = dc.document_id
        WHERE d.organization_id = :org
        ORDER BY dc.embedding <=> (:q)::vector
        LIMIT {top_k}
        """
    )
    rows = db.execute(sql, {"q": qvec_np.tolist(), "org": str(payload.org_id)}).fetchall()

    if not rows:
        grounded_answer = (
            "I don't have information about that in the current organization's knowledge base."
        )
        return AskResponse(answer=grounded_answer)

    snippets: List[str] = [r.content for r in rows]
    scores = [max(0.0, 1.0 - float(r.distance)) for r in rows]

    # If confidence is low, refuse without adding any hotline/contact info
    refusal_threshold = float(os.getenv("RAG_REFUSAL_THRESHOLD", "0.65"))
    if scores[0] < refusal_threshold:
        msg = "I don't have enough information to answer from this organization's data."
        return AskResponse(answer=msg)

    # Build grounded prompt and ask Gemini
    prompt = make_prompt(payload.question, snippets)
    model = get_gemini()
    try:
        result = model.generate_content(prompt)
        answer_text = (getattr(result, "text", "") or "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # Optionally persist the exchange
    try:
        chat = Chat(user_id=payload.user_id, title=payload.question[:80])
        db.add(chat)
        db.flush()
        db.add(ChatMessage(chat_id=chat.id, role="user", content=payload.question))
        citations = [
            {"chunk_id": str(r.chunk_id), "filename": r.filename, "score": s}
            for r, s in zip(rows, scores)
        ]
        db.add(ChatMessage(chat_id=chat.id, role="assistant", content=answer_text, citations=citations))
        db.commit()
    except Exception:
        db.rollback()

    return AskResponse(answer=answer_text.strip())

@app.post("/upload", response_model=UploadResponse)
def upload_document(
    org_id: uuid.UUID = Form(...),
    user_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Only admins of the target organization can upload
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can upload documents")

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

    <hr/>

    <h2>Ask (RAG)</h2>
    <form id="askForm">
      <input type="text" id="org_id" placeholder="Organization ID" required><br><br>
      <input type="text" id="user_id" placeholder="User ID" required><br><br>
      <textarea id="question" placeholder="Your question..." rows="4" cols="60" required></textarea><br><br>
      <button type="submit">Ask</button>
    </form>
    <pre id="answer"></pre>

    <script>
      document.getElementById('askForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const org_id = document.getElementById('org_id').value;
        const user_id = document.getElementById('user_id').value;
        const question = document.getElementById('question').value;
        const res = await fetch('/ask', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ org_id, user_id, question })
        });
         const data = await res.json();
         document.getElementById('answer').textContent = data.answer || JSON.stringify(data);
      });
    </script>
  </body>
</html>
    """


@app.on_event("startup")
def _ensure_indexes():
    with engine.begin() as conn:
       
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
    from admin_auth import hash_password
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash the password
    password_hash = hash_password(payload.password)
    
    user = User(
        username=payload.username,
        password_hash=password_hash,
        role=payload.role,
        organization_id=payload.organization_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username}



@app.get("/health")
def health_check():
    return {"status": "ok", "message": "RAG backend is running"}