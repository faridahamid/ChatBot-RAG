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
  hi, hello, hey, bonjour, salut, hola, hallo,صباح الخير,السلام عليكم
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
    chat_history: Optional[List[Tuple[str, str]]] = None
) -> str:
    """
    Build the final prompt. Language handling and greeting-only logic are handled by the model per SYSTEM_RULES.
    """
    # join snippets or provide an explicit none marker (lets the model do greeting-only or "don't know")
    ctx_joined = "\n\n---\n\n".join(context_snippets) if context_snippets else "(none)"

    history_block = ""
    if chat_history:
        lines = []
        for role, text in chat_history:
            lines.append(f"{'User' if role=='user' else 'Assistant'}: {text}")
        history_block = "Conversation so far:\n" + "\n".join(lines) + "\n\n"

    return f"""{SYSTEM_RULES}

{history_block}User message:
{question}

Context snippets:
{ctx_joined}

Decision checklist for you:
1) First, detect the user's language from their last message and reply ONLY in that language.
2) If the message is greeting-only, reply with one friendly line and a brief offer to help (no retrieval).
3) Otherwise, answer strictly from the context snippets; if the answer is not present, say you don't know in the user's language.

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
