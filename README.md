# Multi-Organization RAG Chatbot Platform

A **domain-specific AI chatbot** platform that allows multiple organizations to deploy their own intelligent assistant.  
Each chatbot responds **only** from its organization's uploaded content, ensuring **data isolation**, **context-aware answers**, and **scalable management**.

---

## Overview

This platform enables organizations (e.g., insurance, medical, ML/DL) to upload and manage their own knowledge base.  
Users interact with the chatbot through **text Or Speech**, receiving answers strictly from their organization’s documents.  

Admins retain full control over **content uploads, user management, and feedback review**, while users enjoy a smooth conversational experience with history tracking and fallback handling.

---

## Key Features

### Organization Isolation
Each organization has a separate, siloed knowledge base with no data leakage.  
Users and admins from one organization cannot access the data, documents, or chat history of another organization. This ensures strict data privacy and compliance for multi-tenant deployments.

![Organization Isolation](ScreenShots\Superadmin.png)





---

### Role-Based Access Control (RBAC)
Secure authentication for **admins** and **users**, with strict org-level boundaries.  
Admins manage users and documents within their organization; users can only access chat and their own conversation history.There is a super admin that assign and create the admins for each organization and the admin is the one that creates the users.

![Adding an Admin](ScreenShots\Add_admin.png)

After creating an admin by the super admin or a user by the admin an email is sent to the admin/user (the created one)having the Temporary Password and asking him to change the password.

![Email](ScreenShots\Email.png)

The Change password redirects him/her to change there password and they can't login with the temporary one

![Change Password](ScreenShots\Change_pass.png)




---

### Multi-Format Document Upload
Supports PDF, DOCX, TXT, CSV. Files are processed, chunked, and embedded automatically.  
Admins can upload documents in various formats to build a rich, searchable knowledge base.

![Admin Document Management](ScreenShots\Admin_doc.png)

---

### Retrieval-Augmented Generation (RAG)
Accurate, context-aware answers using Gemini API with organization-specific embeddings.  
When a user asks a question, the system retrieves the most relevant document chunks and sends them, along with the user’s query, to the Gemini API.

![Chatbot](ScreenShots\Chatbot.png)


---

### Feedback System
Users can rate responses, submit comments, and admins can review and mark feedback.  
This helps monitor answer quality and improve the knowledge base.

Admins have statistics about the average rating and the average rating of each user 

![Statistics](ScreenShots\statistics.png)

They can also view the ratings of the users and there comment and mark them as read to improve the quality and monitor the answers of the bot and the user's experience

![View Ratings & read them](ScreenShots\View_Feedback.png)


---

### Chat History
Persistent per-user conversations with timestamps and the ability to revisit past sessions.  
Users can review previous chats, and admins can teat the chatbot and also have history.

---

### Fallback Handling
If the chatbot cannot answer confidently, it returns a fallback message or if the user asks about other organization or data isn't in the present documents.  

![Fallback](ScreenShots\Bot_can't.png)



---


## Speech-to-Text (STT) Support

The platform supports **speech-to-text** input, allowing users to interact with the chatbot using their voice in addition to text.

### How It Works

- The backend integrates the [Whisper](https://github.com/openai/whisper) model for automatic speech recognition.
- Users can record or upload audio queries through the chat interface.
- The audio is transcribed to text using Whisper, and the resulting text is processed as a standard query.
- This enables hands-free and accessible interaction for users in multiple languages.

### Technical Details

- **Model:** The default model is `small`, but this can be configured via the `WHISPER_MODEL` environment variable.
- **Device:** Runs on CPU by default; can be set to GPU if available using the `WHISPER_DEVICE` environment variable.
- **Integration:** The backend uses the `faster-whisper` library for efficient transcription.


**You can view a video for the Voice Interaction via this link:**

[View the voice Interaction](https://youtu.be/E3WK_UXJdPs)


---

## Architecture

The system is divided into multiple components, each responsible for one part of the flow:

- **Frontend** – HTML/CSS-based UI for both user chat interface and admin dashboard.  
- **Backend API** – Python with FastAPI handling auth, document processing, and RAG orchestration.  
- **Database** – PostgreSQL for users, organizations, chat logs, feedback, and documents.  
- **Vector Store** – PostgreSQL with `pgvector` extension for semantic embeddings.  
- **Embeddings** – SentenceTransformers (`distiluse-base-multilingual-cased-v2`) for multilingual embedding generation.  
- **LLM Layer** – Google Gemini API, wrapped with LangChain for RAG pipeline integration.  
- **Document Processing** – PyPDF, python-docx, pandas for text extraction & parsing.  


---

## Core Functionalities

### For Users
- Secure login with organization-based access  
- Ask questions via text  
- Get responses **only** from their organization’s data  
- View full conversation history with timestamps  
- Submit feedback on responses  

### For Admins
- Create, edit, and delete user accounts  
- Assign users to specific organizations  
- Upload, update, and delete documents  
- Tag and categorize uploaded knowledge  
- View unresolved queries and user feedback  

---

## Example Workflow

1. **Admin** uploads documents (PDF, CSV, DOCX, or TXT).  
2. Backend extracts, chunks, and embeds the data with SentenceTransformers into **pgvector**.  
3. **User** logs in and asks a question.  
4. Backend retrieves top-matching chunks from org-specific embeddings.  
5. Retrieved context + user query are passed to **Gemini API**.  
6. Gemini generates a domain-specific, context-aware answer.  
7. If confidence is low → fallback: *"I don't have enough information to answer this."*  



---

## Cross-Lingual Retrieval

The chatbot supports **cross-lingual question answering**.  
A user can ask a question in one language (e.g., Arabic) and still retrieve relevant answers from documents stored in another language (e.g., English).

### How It Works

1. **Embeddings with Cross-Lingual Support**  
   All uploaded documents are converted into vector embeddings using a multilingual SentenceTransformer model.  
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


**You can view the bot answering with different language via thia link:**

[View the bot answering with different languages](https://youtu.be/CWGgWo1UzSM)


---

## Tech Stack

| Layer               | Technology |
|---------------------|------------|
| **Frontend**        | HTML, CSS |
| **Backend API**     | FastAPI (Python) |
| **Database**        | PostgreSQL |
| **Vector DB**       | PostgreSQL + `pgvector` |
| **Embeddings**      | SentenceTransformers (`distiluse-base-multilingual-cased-v2`) |
| **LLM Provider**    | Google Gemini API |
| **Framework**       | LangChain |
| **File Processing** | PyPDF, python-docx, pandas |
| **Authentication**  | bcrypt |

---
## Video: Full Platform Workflow

The following video demonstrates the complete workflow of the Multi-Organization RAG Chatbot Platform.  
It covers the main features, including admin and user registration, document upload, chat interaction, feedback system, speech-to-text functionality, and cross-lingual retrieval.  

[Watch the Full Platform ](https://youtu.be/q7oVBK4CPss)
