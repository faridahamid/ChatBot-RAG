import os
import uuid
from typing import List, Optional, Tuple

from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from database import get_db, engine
from models import Organization, User, DocumentChunk, Document, Chat, ChatMessage, SuperAdmin, Feedback
from schemas import (
    OrgCreate, UserCreate, UploadResponse, AskRequest, AskResponse,
    OrganizationResponse, UserResponse, FeedbackCreate, FeedbackResponse, FeedbackUpdate
)
from ingestion import process_document, process_document_from_bytes, embed_query
from llm import get_gemini, make_prompt, rewrite_query_with_history
from admin_auth import router as admin_router

from langdetect import detect

from faster_whisper import WhisperModel
import soundfile as sf
from scipy.signal import resample_poly
import io

app = FastAPI(title="Multi-Org RAG Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(admin_router)

# ---------- STT (Whisper) ----------
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

try:
    whisper_model = WhisperModel(WHISPER_MODEL_NAME, device=WHISPER_DEVICE, compute_type="int8")
    print(f"Whisper loaded: {WHISPER_MODEL_NAME} on {WHISPER_DEVICE}")
except Exception as e:
    raise RuntimeError(f"Failed to load Whisper model: {e}")

# ---------- FRONTEND ROUTES ----------
@app.get("/", response_class=HTMLResponse)
def welcome_page():
    try:
        with open("Frontend/pages/welcome.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Welcome page not found</h1>", status_code=404)

@app.get("/login", response_class=HTMLResponse)
def login_page():
    try:
        with open("Frontend/pages/login.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Login page not found</h1>", status_code=404)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    try:
        with open("Frontend/pages/dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Dashboard page not found</h1>", status_code=404)

@app.get("/admin-upload", response_class=HTMLResponse)
def admin_upload_page():
    try:
        with open("Frontend/pages/admin_upload.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin upload page not found</h1>", status_code=404)

@app.get("/admin-users", response_class=HTMLResponse)
def admin_users_page():
    try:
        with open("Frontend/pages/admin_users.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin users page not found</h1>", status_code=404)

@app.get("/super-admin", response_class=HTMLResponse)
def super_admin_page():
    try:
        with open("Frontend/pages/super_admin.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Super admin page not found</h1>", status_code=404)

@app.get("/admin-documents", response_class=HTMLResponse)
def admin_documents_page():
    try:
        with open("Frontend/pages/admin_documents.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin documents page not found</h1>", status_code=404)

@app.get("/admin-feedback", response_class=HTMLResponse)
def admin_feedback_page():
    try:
        with open("Frontend/pages/admin_feedback.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin feedback page not found</h1>", status_code=404)

@app.get("/change-password", response_class=HTMLResponse)
def change_password_page():
    try:
        with open("Frontend/pages/change_password.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Password change page not found</h1>", status_code=404)

# ---------- STATIC ----------
@app.get("/css/{filename}")
def get_css(filename: str):
    try:
        return FileResponse(f"Frontend/css/{filename}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="CSS file not found")

@app.get("/js/{filename}")
def get_js(filename: str):
    try:
        return FileResponse(f"Frontend/js/{filename}")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="JavaScript file not found")

# ---------- STT API ----------
@app.post("/stt")
async def stt(file: UploadFile = File(...), translate: Optional[bool] = False):
    try:
        audio_bytes = await file.read()

        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)

        # Mono
        if data.shape[1] > 1:
            data = np.mean(data, axis=1)
        else:
            data = data[:, 0]

        # 16k for Whisper
        if sr != 16000:
            from math import gcd
            g = gcd(16000, sr)
            up, down = 16000 // g, sr // g
            data = resample_poly(data, up, down)

        task = "translate" if translate else "transcribe"
        segments, info = whisper_model.transcribe(
            data,
            language=None,
            task=task,
            vad_filter=True,
            beam_size=5
        )
        text_out = "".join(seg.text for seg in segments).strip()

        return JSONResponse({
            "text": text_out,
            "lang": info.language,
            "lang_prob": float(info.language_probability or 0)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT error: {e}")

# ---------- CHAT MANAGEMENT ----------
@app.post("/chats", response_model=dict)
def create_chat(payload: dict, db: Session = Depends(get_db)):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chat = Chat(user_id=user_id, title="New Chat")
    db.add(chat)
    db.commit()
    db.refresh(chat)

    return {"chat_id": str(chat.id), "title": chat.title, "created_at": chat.created_at.isoformat()}

@app.get("/chats/{user_id}", response_class=JSONResponse)
def get_user_chats(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    chats = db.query(Chat).filter(Chat.user_id == user_id).order_by(Chat.created_at.desc()).all()
    return JSONResponse([
        {
            "chat_id": str(chat.id),
            "title": chat.title,
            "created_at": chat.created_at.isoformat(),
            "message_count": len(chat.messages)
        }
        for chat in chats
    ])

@app.get("/chats/{chat_id}/messages", response_model=list)
def get_chat_messages(chat_id: str, db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()

    return [
        {
            "id": str(msg.id),
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "citations": msg.citations
        }
        for msg in messages
    ]

@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: str, db: Session = Depends(get_db)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    db.delete(chat)
    db.commit()

    return {"message": "Chat deleted successfully"}

# ---------- RAG API with MEMORY ----------
@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    # Validate user and org membership
    user = db.query(User).filter(User.id == payload.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(payload.org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    role = (user.role or "").lower()
    if role not in ("user", "admin"):
        return AskResponse(answer="Your role is not permitted to use the chat.")

    # Choose the chat (reuse latest if none provided)
    if payload.chat_id:
        chat = db.query(Chat).filter(Chat.id == payload.chat_id, Chat.user_id == payload.user_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found or access denied")
    else:
        chat = (
            db.query(Chat)
            .filter(Chat.user_id == payload.user_id)
            .order_by(Chat.created_at.desc())
            .first()
        )
        if not chat:
            chat = Chat(user_id=payload.user_id, title=payload.question[:80])
            db.add(chat)
            db.flush()

    # Language detect
    try:
        qlang = detect(payload.question)
    except Exception:
        qlang = "en"
    lang_label = "Arabic" if qlang == "ar" else "English"

    # --------- Recent chat history (last 8 messages) ---------
    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(8)
        .all()
    )
    history: List[Tuple[str, str]] = [(m.role, m.content) for m in reversed(history_rows)]

    # --------- Rewrite to standalone query for retrieval ---------
    # Provide short recent history + current question to the rewriter
    history_for_rewrite = history[-7:]
    standalone_query = rewrite_query_with_history(payload.question, history_for_rewrite + [("user", payload.question)])

    # --------- Embed (standalone) & retrieve ---------
    qvec = embed_query(standalone_query)
    qvec_np = np.array(qvec, dtype=np.float32)

    top_k = int(os.getenv("RAG_TOP_K", "40"))
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

    def row2score(r):
        return max(0.0, 1.0 - float(r.distance))

    snippets: List[str] = [r.content for r in rows]
    scores = [row2score(r) for r in rows]

    # Fallback: translate to English and retry once if weak/empty
    refusal_threshold = float(os.getenv("RAG_REFUSAL_THRESHOLD", "0.40"))
    need_fallback = (not rows) or (scores and scores[0] < refusal_threshold)
    if need_fallback:
        try:
            model = get_gemini()
            t = model.generate_content(
                f"Translate to English (keep common technical terms as-is):\n\n{standalone_query}"
            )
            q_en = (getattr(t, "text", "") or "").strip()
            if q_en:
                qvec_en = np.array(embed_query(q_en), dtype=np.float32)
                rows_en = db.execute(sql, {"q": qvec_en.tolist(), "org": str(payload.org_id)}).fetchall()
                if rows_en:
                    rows = rows_en
                    snippets = [r.content for r in rows]
                    scores = [row2score(r) for r in rows]
        except Exception:
            pass

    if not rows:
        msg = (
            "لا أملك معلومات حول هذا الموضوع في قاعدة معرفة هذه المؤسسة."
            if qlang == "ar"
            else "I don't have information about that in this organization's knowledge base."
        )
        # persist the attempt
        try:
            db.add(ChatMessage(chat_id=chat.id, role="user", content=payload.question))
            db.add(ChatMessage(chat_id=chat.id, role="assistant", content=msg, citations=[]))
            db.commit()
        except Exception:
            db.rollback()
        return AskResponse(answer=msg)

    # --------- Build prompt with memory (short history) ---------
    keep = int(os.getenv("RAG_LLM_SNIPPETS", "8"))
    history_for_answer = history[-6:]  # keep it compact
    prompt = make_prompt(
        question=payload.question,              # show the original wording
        context_snippets=snippets[:keep],
        lang_hint=lang_label,
        chat_history=history_for_answer
    )

    model = get_gemini()
    try:
        result = model.generate_content(prompt)
        answer_text = (getattr(result, "text", "") or "").strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # --------- Persist exchange ---------
    try:
        db.add(ChatMessage(chat_id=chat.id, role="user", content=payload.question))

        citations = [
            {"chunk_id": str(r.chunk_id), "filename": r.filename, "score": max(0.0, 1.0 - float(r.distance))}
            for r in rows[:keep]
        ]
        db.add(ChatMessage(chat_id=chat.id, role="assistant", content=answer_text, citations=citations))

        # Title on first turn or placeholder
        try:
            msg_count = db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id).count()
            if (msg_count == 0) or (not chat.title) or (chat.title.strip().lower() == "new chat"):
                chat.title = payload.question[:80]
        except Exception:
            pass

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error persisting chat: {e}")

    return AskResponse(answer=answer_text.strip())

# ---------- Upload ----------
@app.post("/upload", response_model=UploadResponse)
def upload_document(
    org_id: uuid.UUID = Form(...),
    user_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can upload documents")
    org = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
    if not org:
        raise HTTPException(status_code=403, detail="Organization is inactive")

    filetype = file.filename.split(".")[-1]
    file_bytes = file.file.read()

    print(f"Processing upload: {file.filename} ({len(file_bytes)} bytes)")

    try:
        result = process_document_from_bytes(
            db=db,
            org_id=str(org_id),
            user_id=str(user_id),
            file_bytes=file_bytes,
            filename=file.filename,
            filetype=filetype,
        )
        print(f"Upload successful: {result}")
        return UploadResponse(**result)
    except ValueError as e:
        if str(e) == "DUPLICATE_DOCUMENT":
            raise HTTPException(status_code=409, detail="Duplicate document for this organization")
        print(f"ValueError during upload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid document: {e}")
    except Exception as e:
        print(f"Error during upload: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/documents/{org_id}")
def list_documents(
    org_id: uuid.UUID,
    user_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can list documents")
    org = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
    if not org:
        raise HTTPException(status_code=403, detail="Organization is inactive")

    documents = db.query(Document).filter(Document.organization_id == org_id).all()

    result = []
    for doc in documents:
        chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
        result.append({
            "id": str(doc.id),
            "filename": doc.filename,
            "filetype": doc.filetype,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "chunk_count": chunk_count,
            "uploaded_by": str(doc.uploaded_by) if doc.uploaded_by else None
        })

    return {"documents": result}

@app.delete("/documents/{document_id}")
def delete_document(
    document_id: uuid.UUID,
    user_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(document.organization_id):
        raise HTTPException(statuscode=403, detail="User does not belong to this organization")
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete documents")
    org = db.query(Organization).filter(Organization.id == user.organization_id, Organization.is_active == True).first()
    if not org:
        raise HTTPException(status_code=403, detail="Organization is inactive")

    try:
        db.delete(document)
        db.commit()
        return {"message": "Document deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

# ---------- DB setup ----------
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
        conn.execute(text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='users' AND column_name='is_active'
                ) THEN
                    ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='organizations' AND column_name='is_active'
                ) THEN
                    ALTER TABLE organizations ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
                END IF;
                UPDATE users SET is_active = TRUE WHERE is_active IS NULL;
                UPDATE organizations SET is_active = TRUE WHERE is_active IS NULL;
            END $$;
            """
        ))

# ---------- Orgs/Users/Feedback ----------
@app.post("/orgs", response_class=JSONResponse)
def create_org(payload: OrgCreate, db: Session = Depends(get_db)):
    org = Organization(name=payload.name, description=payload.description)
    db.add(org)
    db.commit()
    db.refresh(org)
    return JSONResponse({"id": org.id, "name": org.name})

@app.post("/users", response_class=JSONResponse)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    from admin_auth import hash_password
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    org = db.query(Organization).filter(Organization.id == payload.organization_id, Organization.is_active == True).first()
    if not org:
        raise HTTPException(status_code=403, detail="Organization is inactive")
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
    return JSONResponse({"id": user.id, "username": user.username})

@app.post("/feedbacks", response_model=FeedbackResponse)
def create_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    message = db.query(ChatMessage).filter(ChatMessage.id == payload.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if str(message.chat_id) != str(payload.chat_id):
        raise HTTPException(status_code=400, detail="Message does not belong to provided chat")

    existing_feedback = (
        db.query(Feedback)
        .filter(Feedback.message_id == payload.message_id, Feedback.user_id == payload.user_id)
        .first()
    )
    if existing_feedback:
        raise HTTPException(status_code=409, detail="User already gave feedback for this message")

    feedback = Feedback(
        chat_id=payload.chat_id,
        message_id=payload.message_id,
        user_id=payload.user_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(
        id=feedback.id,
        chat_id=feedback.chat_id,
        message_id=feedback.message_id,
        user_id=feedback.user_id,
        username=user.username,
        rating=feedback.rating,
        comment=feedback.comment,
        seen_by_admin=feedback.seen_by_admin,
        created_at=feedback.created_at.isoformat(),
    )

@app.get("/feedbacks/{org_id}", response_model=List[FeedbackResponse])
def get_feedbacks(org_id: uuid.UUID, user_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view feedbacks")
    
    org = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
    if not org:
        raise HTTPException(status_code=403, detail="Organization is inactive")

    feedbacks = db.query(Feedback, User.username).join(User, Feedback.user_id == User.id).filter(
        User.organization_id == org_id
    ).order_by(Feedback.created_at.desc()).all()
    
    result = []
    for feedback, username in feedbacks:
        result.append(FeedbackResponse(
            id=feedback.id,
            chat_id=feedback.chat_id,
            message_id=feedback.message_id,
            user_id=feedback.user_id,
            username=username,
            rating=feedback.rating,
            comment=feedback.comment,
            seen_by_admin=feedback.seen_by_admin,
            created_at=feedback.created_at.isoformat()
        ))
    
    return result

@app.put("/feedbacks/{feedback_id}/seen", response_class=JSONResponse)
def update_feedback_seen(feedback_id: uuid.UUID, user_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update feedbacks")
    
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    feedback_user = db.query(User).filter(User.id == feedback.user_id).first()
    if not feedback_user or str(feedback_user.organization_id) != str(user.organization_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    feedback.seen_by_admin = True
    db.commit()
    db.refresh(feedback)
    return JSONResponse({"feedback_id": str(feedback.id), "seen_by_admin": feedback.seen_by_admin})

@app.get("/feedbacks/{org_id}/stats", response_class=JSONResponse)
def get_feedback_stats(org_id: uuid.UUID, user_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view feedback stats")
    
    org = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
    if not org:
        raise HTTPException(status_code=403, detail="Organization is inactive")

    total_feedbacks = db.query(Feedback).join(User, Feedback.user_id == User.id).filter(
        User.organization_id == org_id
    ).count()
    
    avg_rating = db.query(db.func.avg(Feedback.rating)).join(User, Feedback.user_id == User.id).filter(
        User.organization_id == org_id
    ).scalar()
    
    unread_feedbacks = db.query(Feedback).join(User, Feedback.user_id == User.id).filter(
        User.organization_id == org_id,
        Feedback.seen_by_admin == False
    ).count()
    
    rating_distribution = db.query(
        Feedback.rating,
        db.func.count(Feedback.id)
    ).join(User, Feedback.user_id == User.id).filter(
        User.organization_id == org_id
    ).group_by(Feedback.rating).order_by(Feedback.rating).all()
    
    return JSONResponse({
        "total_feedbacks": total_feedbacks,
        "average_rating": float(avg_rating) if avg_rating else 0,
        "unread_feedbacks": unread_feedbacks,
        "rating_distribution": {str(rating): count for rating, count in rating_distribution}
    })

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "RAG backend is running"}
