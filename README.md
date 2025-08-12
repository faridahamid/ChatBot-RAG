# Multi-Organization RAG Chatbot Platform

A **Domain-specific AI chatbot** platform that allows multiple organizations to deploy their own intelligent assistant.  
Each chatbot responds **only** from its organization's uploaded content, ensuring **data isolation** and **context-aware answers**.

---

## Overview
This platform enables organizations (e.g., insurance, medical, government) to upload and manage their own knowledge base.  
Users interact with the chatbot through **text** (and later voice), receiving answers strictly from their organization’s documents.

---

## Key Features
- **Organization Isolation** – Each org has a completely separate knowledge base and chatbot instance.
- **Role-Based Access Control (RBAC)** – Admins and users have distinct privileges.
- **Multi-Format Document Upload** – Supports PDF, DOCX, TXT, CSV.
- **Document Chunking & Embedding** – Automatic preprocessing for semantic search.
- **RAG (Retrieval-Augmented Generation)** – Accurate, context-aware answers from org-specific data.
- **Feedback System** – Users can rate responses; admins can review for improvements.
- **Chat History** – Persistent per-user conversations.
- **Fallback Handling** – Suggests human contact when data is missing or uncertain.
- **Scalable & Secure** – Designed for horizontal scaling, strict data isolation, and compliance.

---

## Architecture
- **Frontend** – HTML/CSS
- **Backend API** – Python (FastAPI)
- **Database** – PostgreSQL
- **Vector Store** – PostgreSQL `pgvector`
- **Embeddings** – `BAAI/bge-base-en` via SentenceTransformers
- **LLM Layer** – Gemini
- **Document Processing** – PyMuPDF, python-docx, pandas


---


## Core Functionalities
### For Users
- Login and access only their organization’s chatbot
- Ask questions via text (Phase 1) and voice (Phase 3)
- View previous chat history
- Submit feedback on answers

### For Admins
- Manage users (create/edit/delete)
- Upload, edit, delete documents
- View unresolved queries & feedback

---

##  Example Workflow
1. **Admin** uploads organization-specific documents.
2. System chunks text & generates embeddings stored in an org-specific vector DB.
3. **User** asks: *"What are the claim requirements?"*
4. Backend retrieves relevant chunks, sends to LLM with org context.
5. LLM responds based only on that org’s documents.
6. If no answer → fallback: *"I Don't have enough information to answer this."*

---

## Tech Stack
| Layer               | Technology |
|---------------------|------------|
| Frontend            | HTML/CSS |
| Backend API         | FastAPI |
| Database            | PostgreSQL |
| Vector DB           | PostgreSQL + `pgvector` |
| Embeddings          | SentenceTransformers (`BAAI/bge-base-en`) |
| LLM Provider        | Gemini |
| Framework           | LangChain |
| File Processing     | PyMuPDF, python-docx, pandas |
|



