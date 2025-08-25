import os
from typing import List, Tuple, Optional
import re
import json

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
    Build the final prompt. The LLM will determine if it's a greeting and respond appropriately.
    """
    # join snippets or provide an explicit none marker
    ctx_joined = "\n\n---\n\n".join(context_snippets) if context_snippets else "(no relevant context)"

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

CRITICAL INSTRUCTIONS:
1) FIRST, determine if this is a greeting/small talk OR a substantive question
2) FOR GREETINGS (hello, hi, how are you, etc. in any language): 
   - Respond with a friendly greeting ONLY
   - DO NOT use any context snippets
   - DO NOT mention any documents or sources
3) FOR SUBSTANTIVE QUESTIONS:
   - Answer strictly from the context snippets in the user's language
   - If answer is not in context, say you don't know
   - NEVER include file names, sources, or document references in your response
4) YOUR RESPONSE MUST NEVER CONTAIN: "Sources:", file names, or any reference to documents

Now respond with ONLY the appropriate message:
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
    
    
CLASSIFY_RULES = """
You are an intent classifier. Decide if the user's message is ONLY a greeting/small talk
or if it requires an answer (including greeting + a question).

Return STRICT JSON with these keys:
- "intent": "greeting_only" OR "needs_answer"
- "reply": for greeting_only ONLY: a short friendly greeting in the user's language offering help.
          for needs_answer: an empty string "".
- "lang": using the user's message language detect it and answer with it 

Rules:
- If the message includes any question, instruction, or topic beyond greeting → "needs_answer".
- Output JSON ONLY. No markdown, no explanations, no extra text.
"""

def _extract_json_maybe(s: str) -> str:
    
    m = re.search(r'\{.*\}', s, flags=re.DOTALL)
    return m.group(0) if m else s

def classify_message_llm(user_msg: str) -> dict:
    model = get_gemini()
    prompt = f"""{CLASSIFY_RULES}

User message:
{user_msg}

JSON:"""
    out = model.generate_content(prompt)
    txt = (getattr(out, "text", "") or "").strip()
    
    txt = _extract_json_maybe(txt)
    try:
        obj = json.loads(txt)
        if obj.get("intent") in ("greeting_only", "needs_answer") and isinstance(obj.get("reply",""), str):
            return obj
    except Exception:
        pass

    
    is_ar = bool(re.search(r'[\u0600-\u06FF]', user_msg or ""))
    return {
        "intent": "needs_answer",
        "reply": "" if not is_ar else "مرحباً! كيف يمكنني مساعدتك؟",
        "lang": "ar" if is_ar else "en"
    }
    
JUDGE_RULES = """
You are an answerability judge. Decide if the assistant's draft answer provides real information grounded in the given context snippets, or if it effectively says it does not know / that the information isn't available in the context.

Return STRICT JSON with:
- "status": "answerable" OR "unknown"
- "reply_if_unknown": a single short, friendly sentence in the user's language that politely says you don't have this information in the organization's knowledge base and invites the user to rephrase or ask something else.

Guidelines:
- If the draft answer indicates lack of information, refusal to answer due to missing context, or cannot be grounded in the snippets → "unknown".
- Only call "answerable" if the draft contains a substantive answer that is reasonably derivable from the snippets.
- Output JSON ONLY. No extra text.
"""

def judge_answer_llm(user_msg: str, context_snippets: List[str], draft_answer: str) -> dict:
    model = get_gemini()
    snippets_joined = "\n\n---\n\n".join(context_snippets) if context_snippets else "(no relevant context)"
    prompt = f"""{JUDGE_RULES}

User message:
{user_msg}

Context snippets:
{snippets_joined}

Assistant draft answer:
{draft_answer}

JSON:"""
    out = model.generate_content(prompt)
    txt = (getattr(out, "text", "") or "").strip()
    txt = _extract_json_maybe(txt)
    try:
        obj = json.loads(txt)
        if obj.get("status") in ("answerable", "unknown") and isinstance(obj.get("reply_if_unknown",""), str):
            return obj
    except Exception:
        pass
    # Safe fallback: treat as answerable to avoid hiding valid answers
    return {"status": "answerable", "reply_if_unknown": ""}

# ---------- LLM builder for unknown reply when retrieval returned nothing ----------
UNKNOWN_REPLY_RULES = """
You are a helpful assistant. The system found no relevant information in its knowledge base for the user's request.
Reply with ONE short, friendly sentence in the user's language to say that you don't have this information in the organization's knowledge base and they may try rephrasing or asking about a different topic. Do NOT include sources or file names. Plain text only.
"""

def make_unknown_reply_llm(user_msg: str) -> str:
    model = get_gemini()
    prompt = f"""{UNKNOWN_REPLY_RULES}

User message:
{user_msg}

Reply:"""
    out = model.generate_content(prompt)
    txt = (getattr(out, "text", "") or "").strip()
    # If model failed, minimal fallback based on language heuristic
    if not txt:
        return "لا أملك معلومات كافية حول هذا الموضوع في قاعدة المعرفة." if re.search(r'[\u0600-\u06FF]', user_msg or "") else "Sorry, I don't have information about that in the knowledge base."
    return txt
