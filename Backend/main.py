import os
import uuid
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
import re
import json


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
from llm import get_gemini, make_prompt, rewrite_query_with_history, classify_message_llm,judge_answer_llm,make_unknown_reply_llm

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
# Lightweight change-password redirector for email links
@app.get("/change-password", response_class=HTMLResponse)
def change_password_page():
    """
    Serve the standalone Change Password page.
    The page reads ?user_id=... and posts to /change-password.
    """
    try:
        with open("Frontend/pages/change_password.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>Change Password page not found</h1>", status_code=404)


# ---------- STT (Whisper) ----------
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

try:
    whisper_model = WhisperModel(WHISPER_MODEL_NAME, device=WHISPER_DEVICE, compute_type="int8")
    print(f"Whisper loaded: {WHISPER_MODEL_NAME} on {WHISPER_DEVICE}")
except Exception as e:
    raise RuntimeError(f"Failed to load Whisper model: {e}")




# def translate_text_simple(text: str, lang_code: str) -> str:
#     if not lang_code or lang_code.lower().startswith("en"):
#         return text
#     try:
#         model = get_gemini()
#         rsp = model.generate_content(
#             f"Translate the following text into the language with ISO 639-1 code '{lang_code}'. "
#             f"Return only the translation, no quotes or commentary.\n\n{text}"
#         )
#         return (getattr(rsp, "text", "") or "").strip() or text
#     except Exception:
#         return text
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

# @app.get("/admin-upload", response_class=HTMLResponse)
# def admin_upload_page():
#     try:
#         with open("Frontend/pages/admin_upload.html", "r", encoding="utf-8") as f:
#             return HTMLResponse(content=f.read())
#     except FileNotFoundError:
#         return HTMLResponse(content="<h1>Admin upload page not found</h1>", status_code=404)

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

@app.get("/admin-chat", response_class=HTMLResponse)
def admin_chat_page():
    try:
        with open("Frontend/pages/admin-chat.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin chat page not found</h1>", status_code=404)

@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard_page():
    try:
        with open("Frontend/pages/admin_dashboard.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Admin dashboard page not found</h1>", status_code=404)

from uuid import UUID

@app.post("/change-password")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db)
):
    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="Both current and new password are required")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    # Validate UUID
    try:
        user_uuid = UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")

    # Server-side password strength (mirror client rules)
    # min 8, at least one uppercase, lowercase, digit, special
    if len(new_password) < 8 \
       or not re.search(r"[A-Z]", new_password) \
       or not re.search(r"[a-z]", new_password) \
       or not re.search(r"\d", new_password) \
       or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
        raise HTTPException(status_code=400, detail="Password does not meet complexity requirements")

    # Lookup user
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    from admin_auth import verify_password, hash_password
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Update password
    user.password_hash = hash_password(new_password)
    try:
        if hasattr(user, "must_change_password"):
            user.must_change_password = False
    except Exception:
        pass

    db.commit()

    # Frontend expects a redirect instruction; welcome page is "/"
    return JSONResponse({"message": "Password changed successfully", "redirect": "/"})
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
            vad_filter=False,
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

@app.put("/chats/{chat_id}/title")
def update_chat_title(chat_id: str, payload: dict, db: Session = Depends(get_db)):
    user_id = payload.get("user_id")
    title = payload.get("title")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    
    # Validate title length
    if len(title) > 100:
        raise HTTPException(status_code=400, detail="Title is too long. Maximum 100 characters allowed.")
    
    # Verify the chat belongs to the user
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")
    
    # Update the title
    chat.title = title
    db.commit()
    
    return {"message": "Chat title updated successfully", "title": title}

# ---------- RAG API with MEMORY ----------

@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)):
    # 1) Validate user & org
    user = db.query(User).filter(User.id == payload.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(payload.org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    if (user.role or "").lower() not in ("user", "admin"):
        return AskResponse(answer="Your role is not permitted to use the chat.")

    # 2) Get (or create) chat
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

    # 3) LLM decides if greeting-only (early exit; NO retrieval; NO sources)
    cls = classify_message_llm(payload.question)
    if cls.get("intent") == "greeting_only":
        greet = cls.get("reply") or ("مرحباً! كيف يمكنني مساعدتك؟" if re.search(r'[\u0600-\u06FF]', payload.question) else "Hi! How can I help you today?")
        try:
            db.add(ChatMessage(chat_id=chat.id, role="user", content=payload.question))
            db.add(ChatMessage(chat_id=chat.id, role="assistant", content=greet, citations=[]))
            db.commit()
        except Exception:
            db.rollback()
        return AskResponse(answer=greet, sources=[])

    # 4) Recent history for rewrite + answer prompt
    history_rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(8)
        .all()
    )
    history: List[Tuple[str, str]] = [(m.role, m.content) for m in reversed(history_rows)]

    # 5) Rewrite to standalone query
    history_for_rewrite = history[-7:]
    standalone_query = rewrite_query_with_history(
        payload.question, history_for_rewrite + [("user", payload.question)]
    )

    # 6) Embed & retrieve top-K chunks
    qvec = embed_query(standalone_query)
    qvec_np = np.array(qvec, dtype=np.float32)

    top_k = int(os.getenv("RAG_TOP_K", "40"))
    rows = db.execute(
        text(f"""
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
        """),
        {"q": qvec_np.tolist(), "org": str(payload.org_id)}
    ).fetchall()

    # 6.a) No retrieved rows → ask LLM to produce a polite unknown reply (NO sources)
    if not rows:
        unknown_reply = make_unknown_reply_llm(payload.question)
        try:
            db.add(ChatMessage(chat_id=chat.id, role="user", content=payload.question))
            db.add(ChatMessage(chat_id=chat.id, role="assistant", content=unknown_reply, citations=[]))
            db.commit()
        except Exception:
            db.rollback()
        return AskResponse(answer=unknown_reply, sources=[])

    def row2score(r): return max(0.0, 1.0 - float(r.distance))
    keep = int(os.getenv("RAG_LLM_SNIPPETS", "8"))
    snippets = [r.content for r in rows]

    # 7) Build answer prompt and get LLM draft answer
    history_for_answer = history[-6:]
    prompt = make_prompt(
        question=payload.question,
        context_snippets=snippets[:keep],
        chat_history=history_for_answer
    )

    model = get_gemini()
    try:
        result = model.generate_content(prompt)
        answer_text = (getattr(result, "text", "") or "").strip()
        # Strip any accidental "Sources:"
        answer_text = re.sub(r'\n*Sources?:.*', '', answer_text, flags=re.IGNORECASE).strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # 8) Ask the LLM-judge if this answer is "answerable" or "unknown"
    verdict = judge_answer_llm(payload.question, snippets[:keep], answer_text)
    is_unknown = verdict.get("status") == "unknown"

    # 9) Prepare sources only if answerable
    citations = []
    unique_filenames = []
    final_answer = answer_text

    if not is_unknown:
        citations = [
            {"chunk_id": str(r.chunk_id), "filename": r.filename, "score": row2score(r)}
            for r in rows[:keep]
        ]
        seen = set()
        for r in rows[:keep]:
            if r.filename and r.filename not in seen:
                unique_filenames.append(r.filename)
                seen.add(r.filename)
        if unique_filenames:
            final_answer += "\n\nSources:\n" + "\n".join(unique_filenames)
        sources_to_return = unique_filenames
    else:
        # إذا الحكم Unknown، لا نضيف مصادر. نُبقي رد الـLLM كما هو (أو نستخدم reply_if_unknown لو تحب).
        sources_to_return = []

    # 10) Persist exchange
    try:
        db.add(ChatMessage(chat_id=chat.id, role="user", content=payload.question))
        db.add(ChatMessage(
            chat_id=chat.id,
            role="assistant",
            content=final_answer,
            citations=citations if not is_unknown else []
        ))
        # عنوان المحادثة
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

    return AskResponse(answer=final_answer, sources=sources_to_return)

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
                    WHERE table_name='users' AND column_name='email'
                ) THEN
                    ALTER TABLE users ADD COLUMN email TEXT;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='users' AND column_name='must_change_password'
                ) THEN
                    ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE;
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
        organization_id=payload.organization_id,
        email=payload.email,
        must_change_password=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return JSONResponse({"id": user.id, "username": user.username})

@app.get("/users/{org_id}", response_class=JSONResponse)
def get_org_users(org_id: uuid.UUID, user_id: uuid.UUID = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if str(user.organization_id) != str(org_id):
        raise HTTPException(status_code=403, detail="User does not belong to this organization")
    if (user.role or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view users")
    
    org = db.query(Organization).filter(Organization.id == org_id, Organization.is_active == True).first()
    if not org:
        raise HTTPException(status_code=403, detail="Organization is inactive")

    users = db.query(User).filter(User.organization_id == org_id, User.is_active == True).all()
    
    result = []
    for user in users:
        result.append({
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })
    
    return result

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

# === List ALL orgs (active + inactive) so the dashboard can show both ===
@app.get("/admin/super-admin/organizations/all", response_class=JSONResponse)
def sa_list_orgs_all(db: Session = Depends(get_db)):
    orgs = db.query(Organization).order_by(Organization.name).all()
    out = []
    for org in orgs:
        admin_count = db.query(User).filter(
            User.organization_id == org.id, User.role == "admin", User.is_active == True
        ).count()
        user_count = db.query(User).filter(
            User.organization_id == org.id, User.role == "user", User.is_active == True
        ).count()
        out.append({
            "id": str(org.id),
            "name": org.name,
            "description": org.description,
            "is_active": bool(org.is_active),
            "admin_count": admin_count,
            "user_count": user_count,
        })
    return JSONResponse(out)


# === RESTORE an org AND all of its admins/users ===
@app.post("/admin/super-admin/organizations/{org_id}/restore", response_class=JSONResponse)
def sa_restore_org(org_id: uuid.UUID, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Reactivate org
    org.is_active = True

    # Reactivate all members (both roles) belonging to this org
    # NOTE: synchronize_session=False is safe for bulk update here
    reactivated_total = (
        db.query(User)
        .filter(User.organization_id == org_id, User.is_active == False)
        .update({User.is_active: True}, synchronize_session=False)
    )

    db.commit()
    db.refresh(org)

    # Counts after restore (active members only)
    admin_count = db.query(User).filter(
        User.organization_id == org_id, User.role == "admin", User.is_active == True
    ).count()
    user_count = db.query(User).filter(
        User.organization_id == org_id, User.role == "user", User.is_active == True
    ).count()

    return JSONResponse({
        "message": "Organization restored",
        "id": str(org.id),
        "reactivated_members": int(reactivated_total),
        "admin_count": admin_count,
        "user_count": user_count,
    })


# === (Optional) SOFT-DELETE an org AND deactivate all members (symmetry) ===
@app.delete("/admin/super-admin/organizations/{org_id}", response_class=JSONResponse)
def sa_soft_delete_org(org_id: uuid.UUID, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.is_active = False

    deactivated_total = (
        db.query(User)
        .filter(User.organization_id == org_id, User.is_active == True)
        .update({User.is_active: False}, synchronize_session=False)
    )

    db.commit()
    db.refresh(org)

    return JSONResponse({
      "message": "Organization deactivated",
      "id": str(org.id),
      "deactivated_members": int(deactivated_total)
    })
    
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "RAG backend is running"}
