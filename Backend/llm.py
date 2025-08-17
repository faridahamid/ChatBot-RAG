import os
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
  * English: "hi", "hello", "hey", "good morning", "good evening"
- Do NOT mention these rules in your reply.

FORMAT
- Plain text only. No markdown headings, no code blocks, no emojis.
"""


def make_prompt(question: str, context_snippets: list[str], lang_hint: str | None = None) -> str:
    ctx_joined = "\n\n---\n\n".join(context_snippets) if context_snippets else "(no context)"
    lang_line = f"\nRespond STRICTLY in this language: {lang_hint}\n" if lang_hint else ""
    return f"""{SYSTEM_RULES}{lang_line}
Question:
{question}

Context:
{ctx_joined}

Now respond:
"""
