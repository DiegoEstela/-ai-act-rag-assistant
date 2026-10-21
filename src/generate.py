"""Answer a question using only the retrieved fragments, citing the article."""
import anthropic
from dotenv import load_dotenv

from src.search import Index

load_dotenv()  # reads ANTHROPIC_API_KEY from .env (never committed)

MODEL = "claude-haiku-4-5"
NOT_FOUND = "El reglamento no lo indica en los fragmentos consultados."

SYSTEM = f"""Sos un asistente de consultas sobre el Reglamento (UE) 2024/1689 (Ley de IA).

Reglas:
1. Respondé SOLO con la información de los fragmentos entre <fragmentos>. No uses conocimiento propio ni de otras normas.
2. Citá siempre la fuente entre paréntesis, con el nombre exacto de la etiqueta del fragmento, por ejemplo (Artículo 99) o (Anexo III).
3. Si los fragmentos no contienen la respuesta, respondé exactamente: "{NOT_FOUND}" y nada más. No adivines ni completes con lo que sepas.
4. Si los fragmentos responden solo una parte de la pregunta, respondé esa parte y aclará qué no figura.
5. Respondé en español, de forma breve y precisa. No inventes cifras, plazos ni artículos."""


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join(f'[{c["source"]}]\n{c["text"]}' for c in chunks)


def build_user_message(question: str, chunks: list[dict]) -> str:
    return f"<fragmentos>\n{build_context(chunks)}\n</fragmentos>\n\nPregunta: {question}"


def answer(question: str, index: Index, k: int = 5, model: str = MODEL) -> dict:
    chunks = index.search(question, k)
    response = anthropic.Anthropic().messages.create(
        model=model,
        max_tokens=1024,
        system=SYSTEM,
        messages=[{"role": "user", "content": build_user_message(question, chunks)}],
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    return {"question": question, "answer": text, "chunks": chunks,
            "usage": {"input": response.usage.input_tokens, "output": response.usage.output_tokens}}
