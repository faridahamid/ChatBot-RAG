# Multi-Organization RAG Chatbot Platform

A **domain-specific AI chatbot** platform that allows multiple organizations to deploy their own intelligent assistant.  
Each chatbot responds **only** from its organization's uploaded content, ensuring **data isolation**, **context-aware answers**, and **scalable management**.

---

## Overview
This platform enables organizations (e.g., insurance, medical, ML/DL) to upload and manage their own knowledge base.  
Users interact with the chatbot through **text** (and later voice), receiving answers strictly from their organization’s documents.  

Admins retain full control over **content uploads, user management, and feedback review**, while users enjoy a smooth conversational experience with history tracking and fallback handling.

---

## Key Features
- **Organization Isolation**  
  Each organization has a separate, siloed knowledge base with no data leakage.  

- **Role-Based Access Control (RBAC)**  
  Secure authentication for **admins** and **users**, with strict org-level boundaries.  

- **Multi-Format Document Upload**  
  Supports PDF, DOCX, TXT, CSV. Files are processed, chunked, and embedded automatically.  

- **RAG (Retrieval-Augmented Generation)**  
  Accurate, context-aware answers using Gemini API with organization-specific embeddings.  

- **Feedback System**  
  Users can rate responses, submit comments, and admins can review and mark feedback.  

- **Chat History**  
  Persistent per-user conversations with timestamps and the ability to revisit past sessions.  

- **Fallback Handling**  
  If the chatbot cannot answer confidently, it returns a fallback message or suggests human support.  
 

---

## Architecture
The system is divided into multiple components, each responsible for one part of the flow:

- **Frontend** – HTML/CSS-based UI for both user chat interface and admin dashboard.  
- **Backend API** – Python with FastAPI handling auth, document processing, and RAG orchestration.  
- **Database** – PostgreSQL for users, organizations, chat logs, feedback, and documents.  
- **Vector Store** – PostgreSQL with `pgvector` extension for semantic embeddings.  
- **Embeddings** – FlagEmbedding (`BAAI/bge-m3`) for multilingual embedding generation.  
- **LLM Layer** – Google Gemini API, wrapped with LangChain for RAG pipeline integration.  
- **Document Processing** – PyMuPDF, python-docx, pandas for text extraction & parsing.  
 

---

##  Core Functionalities
###  For Users
- Secure login with organization-based access  
- Ask questions via text  and voice 
- Get responses **only** from their organization’s data  
- View full conversation history with timestamps  
- Submit feedback on responses  

###  For Admins
- Create, edit, and delete user accounts  
- Assign users to specific organizations  
- Upload, update, and delete documents  
- Tag and categorize uploaded knowledge  
- View unresolved queries and user feedback  

---

##  Example Workflow
1. **Admin** uploads documents (PDF, CSV, DOCX, or TXT).  
2. Backend extracts, chunks, and embeds the data with **BAAI/bge-m3** into **pgvector**.  
3. **User** logs in and asks: *"What do you know about diabetes?"*  
4. Backend retrieves top-matching chunks from org-specific embeddings.  
5. Retrieved context + user query are passed to **Gemini API**.  
6. Gemini generates a domain-specific, context-aware answer.  
7. If confidence is low → fallback: *"I don't have enough information to answer this."*  

---
##  Cross-Lingual Retrieval

The chatbot supports **cross-lingual question answering**.  
This means a user can ask a question in one language (e.g., Arabic) and still retrieve relevant answers from documents stored in another language (e.g., English).

### How It Works
1. **Embeddings with Cross-Lingual Support**  
   All uploaded documents are converted into vector embeddings using **FlagEmbedding (`BAAI/bge-m3`)**, which is designed for **multilingual and cross-lingual semantic similarity**.  
   This allows queries in one language to be matched with documents in a different language.  

2. **Retrieval Step**  
   When a user submits a query (e.g., Arabic), the system converts it into an embedding and searches the **pgvector** database.  
   Because embeddings are cross-lingual, the search can retrieve the **semantically closest English text chunks**.  

3. **Response Generation with Gemini**  
   The retrieved context (even if it’s in English) is passed to **Gemini API**, which can understand multiple languages.  
   Gemini generates a final answer in the **user’s input language** (Arabic, English, or otherwise).  

### Example
- User asks in Arabic:  
  *"ما هي المستندات المطلوبة لتقديم مطالبة التأمين؟"*  
- Backend retrieves the answer from **English policy documents**.  
- Gemini produces a response in Arabic, grounded in the English content.  


This enables **seamless multilingual interaction** without requiring organizations to translate their documents manually.

---
##  Tech Stack
| Layer               | Technology |
|---------------------|------------|
| **Frontend**        | HTML, CSS |
| **Backend API**     | FastAPI (Python) |
| **Database**        | PostgreSQL |
| **Vector DB**       | PostgreSQL + `pgvector` |
| **Embeddings**      | FlagEmbedding (`BAAI/bge-m3`) |
| **LLM Provider**    | Google Gemini API |
| **Framework**       | LangChain |
| **File Processing** | PyMuPDF, python-docx, pandas |
| **Authentication**  | bcrypt |


---

