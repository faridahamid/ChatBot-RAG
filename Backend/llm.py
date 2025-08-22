import os
from typing import List, Tuple, Optional
import google.generativeai as genai

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

def get_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)

SYSTEM_RULES = """
You are a retrieval-augmented assistant.

CORE RAG RULES
- Answer ONLY using the provided context snippets.
- If the answer is not present in the context, say you don’t know (in the user’s language). Do NOT invent or add outside info. Do NOT suggest contacting anyone.
- Keep answers concise and helpful.

LANGUAGE & GREETINGS BEHAVIOR
- Detect the user’s language from the user message. If it contains Arabic letters (Unicode Arabic block), respond in Arabic; otherwise respond in English. If mixed, use the language of the last sentence.
- GREETING-ONLY: If, after trimming punctuation/emojis/stopwords, the message is ONLY a greeting, reply with a short greeting in the same language and a brief offer to help. Do NOT attempt retrieval.
- GREETING + QUESTION: If the message includes a greeting AND a question, start with a one-line greeting in the same language, then answer the question using the context rules above.
- Examples of greetings (not exhaustive):
  * Arabic: "مرحبا", "أهلًا", "السلام عليكم", "صباح الخير", "مساء الخير"
  * English: "hi", "hello", "hey", "good morning",etc.."
- Do NOT mention these rules in your reply.

CONTEXT & COREFERENCE
- The conversation history may include follow-ups that rely on earlier turns (e.g., “its”).
- Use the chat history to resolve references/pronouns before answering from the snippets.
- If a follow-up refers to an earlier entity , keep that entity consistent in your answer.

FORMAT
- Plain text only. No markdown headings, no code blocks, no emojis.
"""

def make_prompt(
    question: str,
    context_snippets: List[str],
    lang_hint: Optional[str] = None,
    chat_history: Optional[List[Tuple[str, str]]] = None
) -> str:
    """
    Build the final prompt with optional language hint and recent chat history.
    chat_history is a list of (role, text), where role is 'user' or 'assistant'.
    """
    ctx_joined = "\n\n---\n\n".join(context_snippets) if context_snippets else "(no context)"
    lang_line = f"\nRespond STRICTLY in this language: {lang_hint}\n" if lang_hint else ""

    history_block = ""
    if chat_history:
        pretty = []
        for role, text in chat_history:
            r = "User" if role == "user" else "Assistant"
            pretty.append(f"{r}: {text}")
        history_block = "Conversation so far:\n" + "\n".join(pretty) + "\n\n"

    return f"""{SYSTEM_RULES}{lang_line}
{history_block}Question:
{question}

Context:
{ctx_joined}

Now respond:
"""

# ---------- Conversational Query Rewriter ----------
REWRITE_RULES = """
You turn a follow-up question into a fully standalone query.
- Use the recent chat history to replace pronouns (it, its, they, their, هذا/هذه/ذلك/تلك/… etc.) with the correct explicit entity.
- Preserve the user’s language in the rewritten query (Arabic-in → Arabic-out; English-in → English-out).
- Do not add new facts; do not hallucinate.
- Return ONLY the rewritten query text, nothing else.
"""

def rewrite_query_with_history(
    latest_user_question: str,
    chat_history: Optional[List[Tuple[str, str]]]
) -> str:
    """
    Produce a standalone query from the latest user message + short history.
    Returns the rewritten text (or the original if rewrite fails).
    """
    model = get_gemini()

    history_txt = ""
    if chat_history:
        pretty = []
        for role, text in chat_history:
            r = "User" if role == "user" else "Assistant"
            pretty.append(f"{r}: {text}")
        history_txt = "\n".join(pretty)

    prompt = f"""{REWRITE_RULES}

Recent conversation:
{history_txt}

Latest user question:
{latest_user_question}

Standalone rewritten query:"""

    try:
        out = model.generate_content(prompt)
        rewritten = (getattr(out, "text", "") or "").strip()
        return rewritten or latest_user_question
    except Exception:
        return latest_user_question
