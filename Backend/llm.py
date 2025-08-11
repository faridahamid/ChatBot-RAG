# llm.py
import os
import google.generativeai as genai

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # fast & cheap; use -pro for higher quality

def get_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


SYSTEM_RULES = """You are a retrieval-augmented assistant.
 - Answer ONLY using the provided context snippets.
 - If the answer isn’t in the context, say you don’t know. Do not invent or suggest contacts."""

def make_prompt(question: str, context_snippets: list[str]) -> str:
    ctx_joined = "\n\n---\n\n".join(context_snippets) if context_snippets else "(no context)"
    return f"""{SYSTEM_RULES}

Question:
{question}

Context:
{ctx_joined}

Now respond:
"""
